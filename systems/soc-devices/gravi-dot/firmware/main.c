/**
 * gravi_dot/main.c — Gravi Dot portable relative gravimeter
 *
 * STM32G474RET6 main firmware. FreeRTOS tasks:
 *   gravity_task   — 250 Hz ADXL355 SPI sampling, 30 s stack averaging
 *   thermal_task   — Peltier PID loop (10 Hz) → 35 °C ±0.05 °C
 *   correction_task— full gravimetric correction pipeline
 *   display_task   — SH1106 OLED UI (10 Hz)
 *   gps_task       — ESP32-C3 UART protocol (GPS NMEA + PPS sync)
 *   sdlog_task     — FAT32 CSV logging
 *   ble_task       — BLE station notifications via ESP32-C3
 *
 * Build: see firmware/CMakeLists.txt
 */

#include "main.h"
#include <math.h>
#include <string.h>
#include <stdio.h>
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "fatfs.h"
#include "adxl355.h"
#include "scl3300.h"
#include "ms5837.h"
#include "ds18b20.h"
#include "sh1106.h"
#include "neom9n.h"
#include "cordic_math.h"
#include "gravity_corrections.h"

/* ── Global state ─────────────────────────────────────────────────── */

typedef struct {
    double lat_deg;       /* WGS84 latitude  (degrees)            */
    double lon_deg;       /* WGS84 longitude (degrees)            */
    double alt_m;         /* GPS elevation (metres)              */
    uint32_t unix_time;   /* GPS time (seconds since epoch)      */
    float   pressure_hpa; /* MS5837 barometer                    */
    float   temp_sensor;  /* ADXL355 block temperature (°C)      */
    float   tilt_x_deg;   /* SCL3300 tilt                        */
    float   tilt_y_deg;   /* SCL3300 tilt                        */
    float   g_z_mgal;     /* raw vertical gravity (μGal→mGal)    */
    float   g_x_mgal;
    float   g_y_mgal;
    float   rms_vibration;/* RMS of 30 s stack (quality metric)  */
    float   g_corrected;  /* final corrected δg (mGal)           */
    float   residual;     /* residual anomaly vs base (mGal)     */
    uint8_t station_type; /* STATION_BASE / STATION_SURVEY       */
    uint8_t valid;
} gravity_station_t;

static gravity_station_t  g_last_station;
static gravity_station_t  g_base_start;
static gravity_station_t  g_base_end;
static uint8_t            g_base_set = 0;
static uint16_t           g_station_count = 0;

/* 30 s @ 250 Hz = 7500 samples per axis */
#define SAMPLE_RATE_HZ   250
#define STACK_SAMPLES    (SAMPLE_RATE_HZ * 30)
#define AXES             3

static volatile int16_t  g_stack_x[STACK_SAMPLES];
static volatile int16_t  g_stack_y[STACK_SAMPLES];
static volatile int16_t  g_stack_z[STACK_SAMPLES];
static volatile uint32_t g_stack_idx = 0;
static volatile uint8_t  g_acquiring = 0;
static volatile uint8_t  g_stack_full = 0;

/* queues */
static QueueHandle_t s_correction_q;   /* gravity_station_t */
static QueueHandle_t s_display_q;      /* gravity_station_t */
static QueueHandle_t s_sdlog_q;        /* gravity_station_t */
static QueueHandle_t s_ble_q;          /* gravity_station_t */

/* latest GPS (updated by gps_task) */
static volatile double   s_gps_lat = 0, s_gps_lon = 0, s_gps_alt = 0;
static volatile uint32_t s_gps_time = 0;
static volatile uint8_t  s_gps_fix = 0;

/* thermal block temperature (from thermal_task) */
static volatile float    s_block_temp = 25.0f;
static volatile uint8_t  s_thermal_stable = 0;

/* Peltier PID state */
static float s_pid_integral = 0.0f;
static float s_pid_prev_err = 0.0f;
#define THERMAL_SETPOINT  35.0f
#define PID_KP  8.0f
#define PID_KI  0.5f
#define PID_KD  2.0f

/* ── Hardware handles ─────────────────────────────────────────────── */

extern SPI_HandleTypeDef hspi1;   /* ADXL355 + SCL3300 */
extern SPI_HandleTypeDef hspi2;   /* microSD */
extern I2C_HandleTypeDef hi2c1;   /* MS5837 */
extern I2C_HandleTypeDef hi2c2;   /* SH1106 OLED */
extern UART_HandleTypeDef huart2; /* ESP32-C3 */
extern TIM_HandleTypeDef htim8;   /* HRTIM → Peltier PWM */

/* ── Helper: compute mean + RMS of an int16 stack ─────────────────── */

static void stack_stats(const volatile int16_t *buf, uint32_t n,
                        double *mean, double *rms)
{
    double sum = 0, sum_sq = 0;
    for (uint32_t i = 0; i < n; i++) {
        double v = (double)buf[i];
        sum    += v;
        sum_sq += v * v;
    }
    double m = sum / (double)n;
    *mean = m;
    double var = (sum_sq / (double)n) - (m * m);
    *rms = (var > 0) ? sqrt(var) : 0.0;
}

/* outlier rejection: compute mean, then recompute excluding >3σ samples */
static void stack_stats_robust(const volatile int16_t *buf, uint32_t n,
                               double *mean, double *rms)
{
    double m0, r0;
    stack_stats(buf, n, &m0, &r0);
    if (r0 < 1.0) { *mean = m0; *rms = r0; return; }

    double sum = 0, sum_sq = 0;
    uint32_t cnt = 0;
    double thresh = 3.0 * r0;
    for (uint32_t i = 0; i < n; i++) {
        double v = (double)buf[i];
        if (fabs(v - m0) <= thresh) {
            sum    += v;
            sum_sq += v * v;
            cnt++;
        }
    }
    if (cnt < n / 2) { *mean = m0; *rms = r0; return; } /* too noisy */
    double m = sum / (double)cnt;
    double var = (sum_sq / (double)cnt) - (m * m);
    *mean = m;
    *rms = (var > 0) ? sqrt(var) : 0.0;
}

/* ── ADXL355 conversion: raw int16 → milli-g ──────────────────────── */
/* ADXL355: 20-bit, ±2g range, 256 000 LSB/g (in 20-bit). We read the  */
/* upper 16 bits of the 20-bit value → 64 LSB/g at 16-bit truncation.  */
/* 1 mg = 9.80665 mGal → multiply mg by 9.80665 to get mGal.           */
#define ADXL355_LSB_PER_G_16B  64.0   /* 16-bit truncated sensitivity  */
#define MGAL_PER_MG            0.980665

static double raw_to_mgal(int16_t raw)
{
    double mg = (double)raw / ADXL355_LSB_PER_G_16B * 1000.0; /* → mg */
    return mg * MGAL_PER_MG;                                    /* → mGal */
}

/* ── gravity_task ─────────────────────────────────────────────────── */
/* 250 Hz ADXL355 sampling into ring stack. When STATION button is    */
/* pressed, g_acquiring=1 triggers a full 30 s capture, then the      */
/* stack is processed and a station record is queued.                  */

static void gravity_task(void *arg)
{
    (void)arg;
    adxl355_init(&hspi1);
    adxl355_set_range(ADXL355_RANGE_2G);
    adxl355_set_odr(ADXL355_ODR_250_HZ);

    int16_t x, y, z;
    uint32_t last_sample = 0;

    for (;;) {
        uint32_t now = HAL_GetTick();
        if (now - last_sample >= 4) {  /* 250 Hz = 4 ms */
            last_sample = now;

            if (adxl355_read_xyz(&hspi1, &x, &y, &z) == ADXL355_OK) {
                uint32_t idx = g_stack_idx;
                g_stack_x[idx] = x;
                g_stack_y[idx] = y;
                g_stack_z[idx] = z;
                g_stack_idx = (idx + 1) % STACK_SAMPLES;

                if (g_acquiring && g_stack_idx == 0) {
                    /* 30 s stack complete */
                    g_stack_full = 1;
                    g_acquiring = 0;
                }
            }
        }

        if (g_stack_full) {
            g_stack_full = 0;

            double mx, my, mz, rx, ry, rz;
            stack_stats_robust(g_stack_x, STACK_SAMPLES, &mx, &rx);
            stack_stats_robust(g_stack_y, STACK_SAMPLES, &my, &ry);
            stack_stats_robust(g_stack_z, STACK_SAMPLES, &mz, &rz);

            gravity_station_t st;
            memset(&st, 0, sizeof(st));

            st.g_z_mgal = (float)raw_to_mgal((int16_t)mz);
            st.g_x_mgal = (float)raw_to_mgal((int16_t)mx);
            st.g_y_mgal = (float)raw_to_mgal((int16_t)my);
            st.rms_vibration = (float)sqrt((rx*rx + ry*ry + rz*rz) / 3.0)
                             / ADXL355_LSB_PER_G_16B * 1000.0f; /* mg RMS */

            /* fill in GPS + environment (latest values) */
            st.lat_deg     = s_gps_lat;
            st.lon_deg     = s_gps_lon;
            st.alt_m       = s_gps_alt;
            st.unix_time   = s_gps_time;
            st.temp_sensor = s_block_temp;
            st.pressure_hpa = ms5837_read_pressure(&hi2c1);
            scl3300_read_tilt(&hspi1, &st.tilt_x_deg, &st.tilt_y_deg);
            st.valid = 1;
            st.station_type = g_station_count == 0 ? STATION_BASE : STATION_SURVEY;

            /* queue for correction, display, sdlog, ble */
            xQueueSend(s_correction_q, &st, 0);
        }

        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

/* ── thermal_task ─────────────────────────────────────────────────── */
/* PID loop for Peltier thermal block. 10 Hz. Reads NTC via ADC, drives */
/* DRV8833 via HRTIM PWM.                                              */

static void thermal_task(void *arg)
{
    (void)arg;
    float dt = 0.1f;  /* 10 Hz */

    for (;;) {
        /* Read NTC temperature from ADC (PA0) */
        float ntc_v = adc_read_ntc_voltage();
        float temp = ntc_to_celsius(ntc_v);
        s_block_temp = temp;

        float err = THERMAL_SETPOINT - temp;
        s_pid_integral += err * dt;
        /* anti-windup clamp */
        if (s_pid_integral > 100.0f) s_pid_integral = 100.0f;
        if (s_pid_integral < -100.0f) s_pid_integral = -100.0f;
        float deriv = (err - s_pid_prev_err) / dt;
        s_pid_prev_err = err;

        float output = PID_KP * err + PID_KI * s_pid_integral + PID_KD * deriv;
        /* clamp 0–100% (heating only — Peltier hot side toward block) */
        if (output < 0) output = 0;
        if (output > 100) output = 100;

        peltier_set_pwm((uint8_t)output);

        /* stability flag: within ±0.05 °C for 10 consecutive samples */
        static uint8_t stable_cnt = 0;
        if (fabs(err) < 0.05f) stable_cnt++;
        else stable_cnt = 0;
        s_thermal_stable = (stable_cnt >= 10) ? 1 : 0;

        /* also read DS18B20 array for gradient monitoring */
        float temps[4];
        ds18b20_read_all(temps);
        (void)temps;

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* ── correction_task ──────────────────────────────────────────────── */
/* Runs the full gravimetric correction pipeline.                      */

static void correction_task(void *arg)
{
    (void)arg;
    gravity_station_t st;

    for (;;) {
        if (xQueueReceive(s_correction_q, &st, portMAX_DELAY) == pdTRUE) {
            if (!st.valid) continue;

            /* 1. Tilt projection */
            double theta_x = st.tilt_x_deg * M_PI / 180.0;
            double theta_y = st.tilt_y_deg * M_PI / 180.0;
            double g_vert = st.g_z_mgal * cordic_cos(theta_x) * cordic_cos(theta_y)
                          + st.g_x_mgal * cordic_sin(theta_x)
                          + st.g_y_mgal * cordic_sin(theta_y);

            /* 2. Temperature correction (factory-calibrated coefficient) */
            double kT = 0.0005; /* 0.5 mGal/°C — stored in flash calibration */
            double dT = st.temp_sensor - 25.0; /* calibration reference 25 °C */
            double g_temp = g_vert - kT * dT;

            /* 3. Pressure (atmosphere) correction */
            double g_atm = 0.000003 * (st.pressure_hpa - 1013.25); /* mGal/hPa */

            /* 4. Drift correction (linear, base-loop) */
            double g_drift = 0.0;
            if (g_base_set && g_base_end.valid) {
                double t_span = (double)(g_base_end.unix_time - g_base_start.unix_time);
                if (t_span > 0) {
                    double frac = (double)(st.unix_time - g_base_start.unix_time) / t_span;
                    double drift_rate = (g_base_end.g_corrected - g_base_start.g_corrected);
                    g_drift = drift_rate * frac;
                }
            }

            /* 5. Latitude correction (WGS84 normal gravity) */
            double lat = st.lat_deg * M_PI / 180.0;
            double sl = cordic_sin(lat);
            double sl2 = sl * sl;
            double gamma0 = 978032.677 * (1.0 + 0.00193185138639 * sl2)
                          / cordic_sqrt(1.0 - 0.00669437999014 * sl2);

            /* 6. Free-air correction */
            double g_fa = 0.3086 * st.alt_m;

            /* 7. Bouguer correction (ρ = 2670 kg/m³ default) */
            double rho = 2670.0;
            double g_boug = 0.04191 * rho * 0.001 * st.alt_m; /* mGal */

            /* 8. Earth-tide correction (Longman simplified) */
            double g_tide = longman_tide(st.unix_time, st.lat_deg, st.lon_deg);

            /* 9. Final corrected gravity */
            double g_corr = g_temp - g_atm - g_drift - g_tide;
            st.g_corrected = (float)g_corr;

            /* 10. Residual anomaly = g_corr - gamma0 - g_fa - g_boug */
            st.residual = (float)(g_corr - gamma0 - g_fa - g_boug);

            /* store as last station */
            g_last_station = st;

            /* if base station, store appropriately */
            if (st.station_type == STATION_BASE) {
                if (g_base_set == 0) {
                    g_base_start = st;
                    g_base_set = 1;
                } else {
                    g_base_end = st;
                    /* retroactively correct drift for all stations */
                    /* (in production: re-process stored stations) */
                }
            }
            g_station_count++;

            /* forward to display, sdlog, ble */
            xQueueSend(s_display_q, &st, 0);
            xQueueSend(s_sdlog_q, &st, 0);
            xQueueSend(s_ble_q, &st, 0);
        }
    }
}

/* ── display_task ─────────────────────────────────────────────────── */

static void display_task(void *arg)
{
    (void)arg;
    sh1106_init(&hi2c2);
    sh1106_clear();
    gravity_station_t st;
    memset(&st, 0, sizeof(st));

    for (;;) {
        xQueueReceive(s_display_q, &st, pdMS_TO_TICKS(100));

        sh1106_clear();
        char line[22];

        /* Line 1: status */
        if (!s_thermal_stable) {
            snprintf(line, sizeof(line), "STABILIZING %.1fC", s_block_temp);
        } else if (s_gps_fix) {
            snprintf(line, sizeof(line), "READY  %d stn", g_station_count);
        } else {
            snprintf(line, sizeof(line), "NO GPS  %d stn", g_station_count);
        }
        sh1106_draw_string(0, 0, line, 1);

        /* Line 2: corrected g */
        snprintf(line, sizeof(line), "g: %.1f mGal", st.g_corrected);
        sh1106_draw_string(0, 12, line, 1);

        /* Line 3: residual anomaly */
        snprintf(line, sizeof(line), "dg: %.1f uGal", st.residual * 1000.0f);
        sh1106_draw_string(0, 24, line, 1);

        /* Line 4: vibration quality */
        snprintf(line, sizeof(line), "vib: %.2f mg", st.rms_vibration);
        sh1106_draw_string(0, 36, line, 1);

        /* Line 5: battery + drift */
        float bat = adc_read_battery_voltage();
        snprintf(line, sizeof(line), "BAT %.1fV  D:%s",
                 bat, g_base_set ? "OK" : "--");
        sh1106_draw_string(0, 48, line, 1);

        sh1106_flush();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* ── gps_task ─────────────────────────────────────────────────────── */
/* Communicates with ESP32-C3 over UART2. ESP32-C3 parses NMEA from    */
/* NEO-M9N and sends compact binary packets: lat, lon, alt, time, fix. */

static void gps_task(void *arg)
{
    (void)arg;
    uint8_t rxbuf[64];
    neom9n_packet_t pkt;

    for (;;) {
        /* ESP32-C3 sends binary packets at 1 Hz */
        int len = neom9n_uart_recv(&huart2, &pkt, 1000);
        if (len > 0 && pkt.fix >= 2) {
            s_gps_lat  = pkt.lat;
            s_gps_lon  = pkt.lon;
            s_gps_alt  = pkt.alt;
            s_gps_time = pkt.unix_time;
            s_gps_fix  = 1;
        } else {
            s_gps_fix = 0;
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* ── sdlog_task ───────────────────────────────────────────────────── */

static void sdlog_task(void *arg)
{
    (void)arg;
    FATFS fs;
    FIL fil;
    FRESULT fr;

    fr = f_mount(&fs, "", 1);
    if (fr != FR_OK) {
        /* SD not present — skip logging */
    }

    uint32_t survey_id = HAL_GetTick();
    char fname[32];
    snprintf(fname, sizeof(fname), "survey_%lu.csv", survey_id);

    if (f_open(&fil, fname, FA_WRITE | FA_CREATE_ALWAYS) == FR_OK) {
        /* CSV header */
        f_puts("#,type,lat,lon,alt,time,g_z,g_x,g_y,temp,press,"
               "tilt_x,tilt_y,rms,g_corr,residual\n", &fil);
        f_close(&fil);
    }

    gravity_station_t st;
    char line[256];

    for (;;) {
        if (xQueueReceive(s_sdlog_q, &st, portMAX_DELAY) == pdTRUE) {
            if (f_open(&fil, fname, FA_WRITE | FA_OPEN_APPEND) == FR_OK) {
                int n = snprintf(line, sizeof(line),
                    "%u,%s,%.7f,%.7f,%.2f,%lu,%.3f,%.3f,%.3f,%.3f,%.2f,%.4f,%.4f,%.3f,%.3f,%.3f\n",
                    g_station_count,
                    st.station_type == STATION_BASE ? "BASE" : "STN",
                    st.lat_deg, st.lon_deg, st.alt_m, st.unix_time,
                    st.g_z_mgal, st.g_x_mgal, st.g_y_mgal,
                    st.temp_sensor, st.pressure_hpa,
                    st.tilt_x_deg, st.tilt_y_deg,
                    st.rms_vibration, st.g_corrected, st.residual);
                f_write(&fil, line, n, NULL);
                f_close(&fil);
            }
        }
    }
}

/* ── ble_task ─────────────────────────────────────────────────────── */
/* Sends station records to ESP32-C3 over UART2 for BLE GATT notify.   */

static void ble_task(void *arg)
{
    (void)arg;
    gravity_station_t st;
    uint8_t packet[64];

    for (;;) {
        if (xQueueReceive(s_ble_q, &st, portMAX_DELAY) == pdTRUE) {
            /* pack into binary protocol for ESP32-C3 */
            packet[0] = 0xAA;  /* sync byte */
            packet[1] = 0x55;
            packet[2] = st.station_type;
            memcpy(&packet[3], &st.g_corrected, 4);
            memcpy(&packet[7], &st.residual, 4);
            memcpy(&packet[11], &st.lat_deg, 8);
            memcpy(&packet[19], &st.lon_deg, 8);
            memcpy(&packet[27], &st.alt_m, 8);
            memcpy(&packet[35], &st.unix_time, 4);
            memcpy(&packet[39], &st.rms_vibration, 4);
            packet[43] = 0x0D;  /* terminator */
            HAL_UART_Transmit(&huart2, packet, 44, 100);
        }
    }
}

/* ── Button handling (EXTI) ───────────────────────────────────────── */

void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    if (pin == STATION_BTN_PIN) {
        if (!s_thermal_stable) return;
        g_acquiring = 1;
        g_stack_idx = 0;
    } else if (pin == BASE_BTN_PIN) {
        if (!s_thermal_stable) return;
        g_acquiring = 1;
        g_stack_idx = 0;
        /* mark next station as base */
        g_station_count = (g_base_set) ? g_station_count : 0;
    }
}

/* ── ADC helpers ──────────────────────────────────────────────────── */

static float adc_read_ntc_voltage(void)
{
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    return (float)raw / 4095.0f * 3.3f;
}

static float ntc_to_celsius(float v)
{
    /* 10 kΩ NTC, 10 kΩ pullup to 3.3 V */
    float r = 10000.0f * (3.3f - v) / v;
    float beta = 3950.0f;
    float t = 1.0f / (1.0f / 298.15f + (1.0f / beta) * logf(r / 10000.0f));
    return t - 273.15f;
}

static float adc_read_battery_voltage(void)
{
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);
    return (float)raw / 4095.0f * 3.3f * 2.0f;  /* ÷2 divider */
}

static void peltier_set_pwm(uint8_t pct)
{
    /* HRTIM CHA on TIM8, 0–100% duty */
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim8);
    uint32_t ccr = (arr * pct) / 100;
    __HAL_TIM_SET_COMPARE(&htim8, TIM_CHANNEL_1, ccr);
}

/* ── main() ───────────────────────────────────────────────────────── */

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_SPI1_Init();
    MX_SPI2_Init();
    MX_I2C1_Init();
    MX_I2C2_Init();
    MX_USART2_UART_Init();
    MX_ADC1_Init();
    MX_ADC2_Init();
    MX_TIM8_Init();

    /* queues */
    s_correction_q = xQueueCreate(4, sizeof(gravity_station_t));
    s_display_q    = xQueueCreate(4, sizeof(gravity_station_t));
    s_sdlog_q      = xQueueCreate(8, sizeof(gravity_station_t));
    s_ble_q        = xQueueCreate(4, sizeof(gravity_station_t));

    /* tasks */
    xTaskCreate(gravity_task,    "gravity",    2048, NULL, 5, NULL);
    xTaskCreate(thermal_task,    "thermal",    512,  NULL, 6, NULL);
    xTaskCreate(correction_task, "correct",    1024, NULL, 4, NULL);
    xTaskCreate(display_task,    "display",    512,  NULL, 3, NULL);
    xTaskCreate(gps_task,        "gps",        512,  NULL, 3, NULL);
    xTaskCreate(sdlog_task,      "sdlog",      1024, NULL, 2, NULL);
    xTaskCreate(ble_task,        "ble",        512,  NULL, 2, NULL);

    vTaskStartScheduler();
    for (;;) {}
}

/* ── Clock / peripheral config (Cube-generated stubs) ─────────────── */

void SystemClock_Config(void)
{
    /* HSE 8 MHz → PLL → 170 MHz (M4)
     * Generated by STM32CubeMX — see system_stm32g4xx.c
     */
    RCC_OscInitTypeDef osc = {0};
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 1;
    osc.PLL.PLLN = 42;
    osc.PLL.PLLR = 2;
    osc.PLL.PLLQ = 4;
    HAL_RCC_OscConfig(&osc);

    RCC_ClkInitTypeDef clk = {0};
    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                  | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);
}

/* placeholder pin definitions — see main.h for GPIO map */
#define STATION_BTN_PIN  GPIO_PIN_8
#define BASE_BTN_PIN     GPIO_PIN_9

void MX_GPIO_Init(void)        { /* CubeMX-generated — see main.h */ }
void MX_SPI1_Init(void)        { /* CubeMX-generated */ }
void MX_SPI2_Init(void)        { /* CubeMX-generated */ }
void MX_I2C1_Init(void)        { /* CubeMX-generated */ }
void MX_I2C2_Init(void)        { /* CubeMX-generated */ }
void MX_USART2_UART_Init(void) { /* CubeMX-generated */ }
void MX_ADC1_Init(void)        { /* CubeMX-generated */ }
void MX_ADC2_Init(void)        { /* CubeMX-generated */ }
void MX_TIM8_Init(void)        { /* CubeMX-generated HRTIM */ }

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) { (void)htim; }
void vApplicationStackOverflowHook(TaskHandle_t t, char *n) { (void)t; (void)n; }
void _Error_Handler(const char *f, int l) { (void)f; (void)l; }