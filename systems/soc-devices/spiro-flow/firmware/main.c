/**
 * spiro_flow/main.c — Spiro Flow Portable Electronic Spirometer
 *
 * CH32V203RBT6 (RISC-V RV32IMAC @ 144 MHz, 128 KB flash, 64 KB SRAM)
 *
 * Main firmware — cooperative super-loop with interrupt-driven sampling.
 *
 * Hardware flow:
 *   Patient blows into mouthpiece → Fleisch pneumotach screen
 *   → ΔP across screen measured by SDP810 differential pressure sensor
 *   → I2C → CH32V203 reads pressure @ 250 Hz
 *   → flow = ΔP / R_pneumo
 *   → volume = ∫ flow dt (trapezoidal integration)
 *   → spirometry parameters computed from flow-volume curve
 *   → BTPS correction applied using BME280 ambient data
 *   → results shown on OLED, logged to W25Q128 flash, sent via UART
 *     to ESP32-C3 for BLE/WiFi relay to phone app
 *
 * Maneuver detection:
 *   1. Wait for flow > BLAST_FLOW_THRESH (exhalation start)
 *   2. Capture flow + integrated volume for up to 8 seconds
 *   3. Detect end-of-maneuver (flow < 0.025 L/s for 0.5 s)
 *   4. Back-extrapolate to find true time zero (volume = 0)
 *   5. Compute FVC, FEV1, PEF, FEF25-75, FET, etc.
 *   6. Grade acceptability per ATS/ERS 2019 standard
 *   7. Compare to predicted values (ECSC/ERS 1993 reference equations)
 *   8. Classify pattern: normal / obstructive / restrictive / mixed
 *
 * Build: see firmware/Makefile
 */

#include "main.h"
#include "sdp810.h"
#include "bme280.h"
#include "sh1106.h"
#include "spirometry.h"
#include "flashlog.h"
#include "ble_bridge.h"
#include "buzzer.h"
#include "ws2812.h"

#include <string.h>
#include <math.h>

static const char *TAG = "SPIRO";

/* ── Global state ──────────────────────────────────────────────────── */

volatile spiro_mode_t g_mode = MODE_IDLE;
volatile bool g_measure_trigger = false;
patient_t g_patient = {
    .age_years = 30,
    .height_cm = 175,
    .sex = 0,
    .ethnicity = 0,
    .name = "Patient"
};
maneuver_buffer_t g_maneuver;
spiro_result_t g_result;

/* ambient conditions (updated by BME280 task) */
static float s_ambient_temp = 22.0f;
static float s_ambient_pressure = 760.0f;
static float s_ambient_humidity = 50.0f;

/* latest sensor readings */
static float s_current_flow = 0.0f;
static float s_current_volume = 0.0f;
static float s_current_diff_pa = 0.0f;

/* session counter */
static uint16_t g_session_id = 1;
static uint8_t g_maneuver_count = 0;
static uint8_t g_best_maneuver = 0;
static spiro_result_t g_best_result;

/* timer for 250 Hz sampling */
static volatile uint32_t s_sample_tick = 0;
static volatile bool s_sample_ready = false;

/* ── Timer interrupt (250 Hz sampling) ────────────────────────────── */

/* TIM2 generates interrupt every 4ms (250 Hz)
 * In real CH32V203 HAL:
 *   TIM_TimeBaseInitTypeDef tim;
 *   tim.TIM_Period = (SystemCoreClock / 250) - 1;
 *   tim.TIM_Prescaler = 0;
 *   ...
 *   NVIC_EnableIRQ(TIM2_IRQn);
 */
void TIM2_IRQHandler(void) __attribute__((interrupt));
void TIM2_IRQHandler(void)
{
    /* clear interrupt flag (CH32V203 HAL: TIM_ClearITPendingBit(TIM2, TIM_IT_Update)) */
    s_sample_tick++;
    s_sample_ready = true;
}

/* ── Battery monitoring ────────────────────────────────────────────── */

uint8_t battery_read_pct(void)
{
    /* ADC1 CH1 = PA1, 12-bit, 2:1 voltage divider
     * Vbat = raw * 2 * 3.3 / 4095
     */
    /* In real HAL:
     * ADC_RegularChannelConfig(ADC1, ADC_Channel_1, 1, ADC_SampleTime_239Cycles5);
     * ADC_SoftwareStartConvCmd(ADC1, ENABLE);
     * while(!ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC));
     * uint16_t raw = ADC_GetConversionValue(ADC1);
     */
    static uint16_t s_adc_raw = 2048; /* placeholder; real code reads ADC */
    float vbat = (float)s_adc_raw * 2.0f * 3.3f / 4095.0f;
    float pct = (vbat - 3.0f) / (4.2f - 3.0f) * 100.0f;
    if (pct > 100.0f) pct = 100.0f;
    if (pct < 0.0f)   pct = 0.0f;
    return (uint8_t)(pct + 0.5f);
}

/* ── millis() ──────────────────────────────────────────────────────── */

static uint32_t s_system_tick = 0;

uint32_t millis(void)
{
    return s_system_tick;
}

void delay_ms(uint32_t ms)
{
    /* SysTick-based delay; placeholder uses busy-wait */
    uint32_t start = millis();
    while ((millis() - start) < ms) {
        /* yield / wfi */
    }
}

/* ── Maneuver capture state machine ────────────────────────────────── */

typedef enum {
    CAP_WAIT_BLAST,
    CAP_SAMPLING,
    CAP_WAIT_END,
    CAP_DONE,
} capture_state_t;

static capture_state_t s_cap_state = CAP_WAIT_BLAST;
static uint32_t s_cap_start_tick = 0;
static uint32_t s_last_flow_tick = 0;
static int s_end_counter = 0;

static void reset_maneuver_buffer(void)
{
    memset(&g_maneuver, 0, sizeof(g_maneuver));
    g_maneuver.sample_rate = SAMPLE_RATE_HZ;
}

static void capture_sample(float flow_lps)
{
    if (g_maneuver.n_samples >= MAX_SAMPLES)
        return;

    int i = g_maneuver.n_samples;
    g_maneuver.flow_lps[i] = flow_lps;

    /* trapezoidal integration: V += (flow[i] + flow[i-1])/2 * dt */
    float dt = 1.0f / SAMPLE_RATE_HZ;  /* seconds */
    if (i == 0) {
        g_maneuver.volume_ml[i] = flow_lps * dt * 1000.0f; /* L/s * s * 1000 = mL */
    } else {
        float prev_flow = g_maneuver.flow_lps[i-1];
        float avg_flow = (flow_lps + prev_flow) * 0.5f;
        g_maneuver.volume_ml[i] = g_maneuver.volume_ml[i-1] + avg_flow * dt * 1000.0f;
    }

    g_maneuver.n_samples++;
}

static void process_maneuver(void)
{
    ESP_LOGI(TAG, "Processing maneuver: %d samples, %.1f mL final vol",
             g_maneuver.n_samples,
             g_maneuver.n_samples > 0 ? g_maneuver.volume_ml[g_maneuver.n_samples-1] : 0);

    float ambient[3] = {s_ambient_temp, s_ambient_pressure, s_ambient_humidity};

    spirometry_compute(&g_maneuver, &g_patient, ambient, &g_result);
    g_result.session_id = g_session_id;
    g_result.maneuver_count = ++g_maneuver_count;
    g_result.timestamp = millis() / 1000;
    g_result.valid = true;

    /* Track best maneuver (highest FVC + best grade) */
    if (g_maneuver_count == 1 || g_result.grade > g_best_result.grade ||
        (g_result.grade == g_best_result.grade &&
         g_result.fvc_liters > g_best_result.fvc_liters)) {
        g_best_result = g_result;
        g_best_maneuver = g_maneuver_count;
    }

    /* Log to flash */
    flashlog_write_session(&g_result, &g_maneuver);

    /* Send to BLE bridge */
    ble_bridge_send_result(&g_result);

    /* Buzzer feedback */
    if (g_result.grade >= GRADE_B) {
        buzzer_beep(880, 100);  /* pleasant beep — good maneuver */
    } else {
        buzzer_beep(220, 200);  /* low buzz — retry */
    }

    /* RGB LED */
    if (g_result.grade >= GRADE_A) {
        ws2812_set(0, 80, 0);   /* green */
    } else if (g_result.grade >= GRADE_C) {
        ws2812_set(80, 60, 0);  /* yellow */
    } else {
        ws2812_set(80, 0, 0);   /* red */
    }
}

/* ── Main loop ─────────────────────────────────────────────────────── */

int main(void)
{
    ESP_LOGI(TAG, "=== Spiro Flow Portable Electronic Spirometer ===");
    ESP_LOGI(TAG, "CH32V203RBT6 RISC-V @ 144 MHz");

    /* ── Hardware init ── */

    /* System clock: 144 MHz from 8 MHz HSE via PLL
     * (CH32V203 HAL: SystemCoreClockConfigure(PLL_SOURCE_HSE, 8, 144))
     */
    /* SystemInit() called by startup code; SysTick at 1ms */

    /* I2C1 init at 400 kHz for SDP810, BME280, SH1106 */
    /* i2c1_init(400000); */

    /* USART1 init at 115200 baud for ESP32-C3 bridge */
    /* usart1_init(115200); */

    /* SPI2 init for W25Q128 */
    /* spi2_init(); */

    /* TIM2 init: 250 Hz sampling interrupt */
    /* tim2_init_250hz(); */

    /* ADC1 init for battery */
    /* adc1_init(); */

    /* GPIO init for buttons, LED, buzzer, WS2812 */
    /* gpio_init_all(); */

    /* ── Sensor init ── */
    sdp810_init();
    bme280_init();
    sh1106_init();
    flashlog_init();
    ble_bridge_init();
    buzzer_init();
    ws2812_init();

    ESP_LOGI(TAG, "All subsystems initialized.");

    /* Start SDP810 continuous measurement */
    sdp810_start_continuous();

    /* ── Super-loop ── */
    uint32_t last_ambient_tick = 0;
    uint32_t last_display_tick = 0;
    uint32_t last_ble_tick = 0;

    while (1) {
        uint32_t now = millis();

        /* ── 250 Hz sensor sampling ── */
        if (s_sample_ready) {
            s_sample_ready = false;

            float diff_pa, temp_c;
            if (sdp810_read_pressure(&diff_pa, &temp_c) == 0) {
                s_current_diff_pa = diff_pa;
                /* flow = ΔP / R_pneumo (Pa / (Pa·s/L) = L/s) */
                s_current_flow = diff_pa / PNEUMO_RESISTANCE;

                /* Clamp to valid range */
                if (s_current_flow > FLOW_MAX_LPS)  s_current_flow = FLOW_MAX_LPS;
                if (s_current_flow < FLOW_MIN_LPS)  s_current_flow = FLOW_MIN_LPS;

                /* Update current volume for display */
                /* (full integration only during capture) */
            }
        }

        /* ── Ambient BME280 read every 5s ── */
        if ((now - last_ambient_tick) > 5000) {
            last_ambient_tick = now;
            float t, p, h;
            if (bme280_read(&t, &p, &h) == 0) {
                s_ambient_temp = t;
                s_ambient_pressure = p;
                s_ambient_humidity = h;
                ESP_LOGI(TAG, "Ambient: %.1f°C, %.1f mmHg, %.1f%%RH", t, p, h);
            }
        }

        /* ── Mode state machine ── */
        switch (g_mode) {

        case MODE_IDLE:
            ws2812_set(0, 0, 20);  /* dim blue — idle */
            if (g_measure_trigger) {
                g_measure_trigger = false;
                g_mode = MODE_READY;
                buzzer_coach_start();
                ESP_LOGI(TAG, "Mode → READY (armed for maneuver)");
            }
            break;

        case MODE_READY:
            /* Wait for blast detection (flow > threshold) */
            if (s_current_flow > BLAST_FLOW_THRESH_LPS) {
                g_mode = MODE_CAPTURE;
                s_cap_state = CAP_SAMPLING;
                s_cap_start_tick = now;
                s_last_flow_tick = now;
                s_end_counter = 0;
                reset_maneuver_buffer();
                buzzer_coach_blast();
                ESP_LOGI(TAG, "Blast detected! Capturing maneuver...");
            }
            break;

        case MODE_CAPTURE:
            /* Sample flow into buffer at 250 Hz */
            if (s_sample_ready || s_current_diff_pa != 0) {
                capture_sample(s_current_flow);
                s_current_volume = g_maneuver.n_samples > 0
                    ? g_maneuver.volume_ml[g_maneuver.n_samples-1] : 0;
            }

            /* Check for end of maneuver:
             * flow < 0.025 L/s for 0.5 seconds, or timeout
             */
            if (fabsf(s_current_flow) < 0.025f) {
                s_end_counter++;
            } else {
                s_end_counter = 0;
                s_last_flow_tick = now;
            }

            bool maneuver_end = false;

            /* End condition 1: flow below threshold for 0.5s (125 samples) */
            if (s_end_counter >= 125) {
                maneuver_end = true;
                ESP_LOGI(TAG, "Maneuver end: flow < threshold for 0.5s");
            }

            /* End condition 2: buffer full */
            if (g_maneuver.n_samples >= MAX_SAMPLES) {
                maneuver_end = true;
                ESP_LOGI(TAG, "Maneuver end: buffer full (8s)");
            }

            /* End condition 3: timeout (15s) */
            if ((now - s_cap_start_tick) > (MANEUVER_TIMEOUT_SEC * 1000)) {
                maneuver_end = true;
                ESP_LOGI(TAG, "Maneuver end: timeout");
            }

            if (maneuver_end) {
                process_maneuver();
                g_mode = MODE_RESULTS;
                buzzer_coach_done();
            }
            break;

        case MODE_RESULTS:
            /* Display results; MEASURE button starts new maneuver */
            if (g_measure_trigger) {
                g_measure_trigger = false;
                if (g_maneuver_count >= 3) {
                    /* After 3 maneuvers, go back to idle */
                    g_maneuver_count = 0;
                    g_mode = MODE_IDLE;
                    ESP_LOGI(TAG, "Session complete (3 maneuvers). Best: #%d",
                             g_best_maneuver);
                } else {
                    g_mode = MODE_READY;
                    ESP_LOGI(TAG, "Ready for maneuver #%d", g_maneuver_count + 1);
                }
            }
            /* MODE button → review */
            if (false /* mode_button_pressed */) {
                g_mode = MODE_REVIEW;
            }
            break;

        case MODE_REVIEW:
            /* Show past sessions; button to return */
            if (g_measure_trigger) {
                g_measure_trigger = false;
                g_mode = MODE_IDLE;
            }
            break;

        case MODE_SETTINGS:
            /* Patient parameter entry */
            if (g_measure_trigger) {
                g_measure_trigger = false;
                g_mode = MODE_IDLE;
            }
            break;
        }

        /* ── Display update at 20 Hz ── */
        if ((now - last_display_tick) > 50) {
            last_display_tick = now;
            uint8_t bat = battery_read_pct();

            switch (g_mode) {
            case MODE_IDLE:
                sh1106_draw_idle();
                break;
            case MODE_READY:
                sh1106_draw_ready(bat);
                break;
            case MODE_CAPTURE:
                sh1106_draw_capture(&g_maneuver, s_current_flow, s_current_volume);
                break;
            case MODE_RESULTS:
                sh1106_draw_results(&g_result, bat);
                break;
            case MODE_REVIEW:
                sh1106_draw_results(&g_best_result, bat);
                break;
            case MODE_SETTINGS:
                sh1106_draw_settings(&g_patient, 0);
                break;
            }
        }

        /* ── BLE bridge poll at 10 Hz ── */
        if ((now - last_ble_tick) > 100) {
            last_ble_tick = now;
            ble_bridge_poll();
        }

        /* ── Button polling (100 Hz, debounced) ── */
        /* In real HAL: read GPIO pins, debounce, set g_measure_trigger */
        /* Simplified: placeholder for button polling */
        /*
        static uint8_t btn_meas_state = 1, btn_meas_prev = 1;
        static int meas_debounce = 0;
        uint8_t meas = gpio_get_level(PIN_BTN_MEASURE);
        if (meas != btn_meas_prev) { meas_debounce = 0; btn_meas_prev = meas; }
        if (++meas_debounce >= 5) {
            if (btn_meas_state == 1 && meas == 0) {
                g_measure_trigger = true;
            }
            btn_meas_state = meas;
            meas_debounce = 5;
        }
        */

        s_system_tick++;
    }

    return 0;
}

/* ── ESP logging shim (for portability) ────────────────────────────── */

/* The CH32V203 doesn't have ESP-IDF; this is a lightweight log shim */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) \
    do { \
        printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); \
    } while(0)
#define ESP_LOGW(tag, fmt, ...) \
    do { \
        printf("[%s WARN] " fmt "\n", tag, ##__VA_ARGS__); \
    } while(0)
#define ESP_LOGE(tag, fmt, ...) \
    do { \
        printf("[%s ERR] " fmt "\n", tag, ##__VA_ARGS__); \
    } while(0)
#endif