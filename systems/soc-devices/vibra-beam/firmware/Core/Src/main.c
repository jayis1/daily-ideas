/*
 * main.c — Vibra Beam main application
 * STM32G474RET6
 *
 * Pocket laser Doppler vibrometer (quadrature homodyne Michelson).
 * State machine: BOOT → IDLE → MENU → CALIBRATE → MEASURE →
 *                PROCESS → DISPLAY_RESULT → LOG_STREAM → AUDIO_LISTEN
 */

#include "main.h"
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "config.h"
#include "interferometer.h"
#include "dsp.h"
#include "imu.h"
#include "laser.h"
#include "display.h"
#include "storage.h"
#include "ble_bridge.h"
#include "audio.h"
#include "power.h"
#include "onewire.h"
#include "i2c_util.h"

/* ── Global Handles ─────────────────────────────────────── */
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim8;
UART_HandleTypeDef huart2;
I2S_HandleTypeDef hi2s2;

/* DMA buffers for dual ADC */
static volatile uint16_t adc1_buf[CONFIG_ADC_BLOCK_SAMPLES];
static volatile uint16_t adc2_buf[CONFIG_ADC_BLOCK_SAMPLES];
static volatile uint8_t  adc_block_ready = 0;

/* ── Global State ───────────────────────────────────────── */
volatile device_state_t g_state = STATE_BOOT;
acq_params_t g_params;
measure_result_t g_result;
static iq_block_t g_iq;
static phase_block_t g_phase;
static fft_result_t g_fft;
static modal_result_t g_modal;

/* Button debounce */
static uint32_t last_btn_a = 0;
static uint32_t last_btn_b = 0;
static volatile uint8_t btn_a_flag = 0;
static volatile uint8_t btn_b_flag = 0;

/* Timing */
static uint32_t measure_start_ms = 0;
static uint32_t last_measure_ms = 0;

/* ── Forward declarations ───────────────────────────────── */
static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);
static void MX_ADC2_Init(void);
static void MX_I2C1_Init(void);
static void MX_SPI2_Init(void);
static void MX_TIM3_Init(void);
static void MX_TIM8_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_I2S2_Init(void);

static void run_boot(void);
static void run_idle(void);
static void run_menu(void);
static void run_calibrate(void);
static void run_measure(void);
static void run_process(void);
static void run_display_result(void);
static void run_log_stream(void);
static void run_audio_listen(void);
static void run_fault(void);
static void handle_ble_commands(void);
static void set_status_led(uint8_t r, uint8_t g, uint8_t b);
static void default_params(void);
static void button_a_handler(void);
static void button_b_handler(void);
static void HAL_ADC_LevelOutOfWindowCallback(ADC_HandleTypeDef *h);

/* ── Main ──────────────────────────────────────────────── */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_ADC2_Init();
    MX_I2C1_Init();
    MX_SPI2_Init();
    MX_TIM3_Init();
    MX_TIM8_Init();
    MX_USART2_UART_Init();
    MX_I2S2_Init();

    default_params();
    run_boot();

    g_state = STATE_IDLE;

    while (1) {
        switch (g_state) {
        case STATE_BOOT:
            run_boot();
            g_state = STATE_IDLE;
            break;
        case STATE_IDLE:
            run_idle();
            break;
        case STATE_MENU:
            run_menu();
            break;
        case STATE_CALIBRATE:
            run_calibrate();
            break;
        case STATE_MEASURE:
            run_measure();
            break;
        case STATE_PROCESS:
            run_process();
            break;
        case STATE_DISPLAY_RESULT:
            run_display_result();
            break;
        case STATE_LOG_STREAM:
            run_log_stream();
            break;
        case STATE_AUDIO_LISTEN:
            run_audio_listen();
            break;
        case STATE_FAULT:
            run_fault();
            break;
        default:
            g_state = STATE_IDLE;
            break;
        }

        handle_ble_commands();

        if (btn_a_flag) {
            btn_a_flag = 0;
            button_a_handler();
        }
        if (btn_b_flag) {
            btn_b_flag = 0;
            button_b_handler();
        }

        /* Refresh watchdog */
        HAL_IWDG_Refresh(&hiwdg);
    }
}

/* ── Boot sequence ──────────────────────────────────────── */
static void run_boot(void)
{
    display_init();
    display_boot("Vibra Beam v1.0");

    if (i2c_util_init() != 0) {
        display_boot("I2C FAIL");
        HAL_Delay(2000);
    }

    interferometer_init();
    dsp_init();
    imu_init();
    laser_init();
    storage_init();
    ble_bridge_init();
    audio_init();

    storage_load_params(&g_params);

    /* Enable laser at default safe power */
    laser_set_power_mw(g_params.laser_mw);
    laser_enable();
    shutter_open();

    display_boot("Ready! Aim at target");
    HAL_Delay(1500);
    set_status_led(0, 1, 0); /* green = ready */
}

/* ── Idle ──────────────────────────────────────────────── */
static void run_idle(void)
{
    float temp = onewire_read_temp_c();
    float vbat = power_read_battery_mv();

    display_idle(temp, vbat, g_params.laser_mw);

    /* Safety: if tilt > 45° or lid open, close shutter */
    if (!laser_safety_check()) {
        shutter_close();
        laser_disable();
        g_state = STATE_FAULT;
        return;
    }

    HAL_Delay(100);
}

/* ── Menu ───────────────────────────────────────────────── */
static uint8_t menu_item = 0;
static const char *menu_items[] = {
    "Measure (velocity)",
    "Measure (spectrum)",
    "Audio Listen",
    "Calibrate Fringe",
    "Set Laser Power",
    "Set LP Cutoff",
    "IMU Compensate",
    "FFT Size",
    "BLE Stream",
    "Back"
};
#define MENU_COUNT (sizeof(menu_items)/sizeof(menu_items[0]))

static void run_menu(void)
{
    display_menu(menu_item);
    HAL_Delay(50);
}

static void button_a_handler(void)
{
    if (g_state == STATE_IDLE) {
        g_state = STATE_MENU;
        menu_item = 0;
    } else if (g_state == STATE_MENU) {
        menu_item = (menu_item + 1) % MENU_COUNT;
    } else if (g_state == STATE_DISPLAY_RESULT) {
        g_state = STATE_IDLE;
    } else if (g_state == STATE_LOG_STREAM) {
        g_state = STATE_IDLE;
    } else if (g_state == STATE_AUDIO_LISTEN) {
        audio_stop();
        g_state = STATE_IDLE;
    }
}

static void button_b_handler(void)
{
    if (g_state == STATE_MENU) {
        switch (menu_item) {
        case 0: /* Measure velocity */
            g_params.run_fft = 0;
            g_state = STATE_MEASURE;
            measure_start_ms = HAL_GetTick();
            break;
        case 1: /* Measure spectrum */
            g_params.run_fft = 1;
            g_state = STATE_MEASURE;
            measure_start_ms = HAL_GetTick();
            break;
        case 2: /* Audio listen */
            g_state = STATE_AUDIO_LISTEN;
            audio_start();
            break;
        case 3: /* Calibrate */
            g_state = STATE_CALIBRATE;
            break;
        case 4: /* Set laser power */
            g_params.laser_mw = (g_params.laser_mw >= CONFIG_LASER_MAX_MW)
                              ? CONFIG_LASER_DEFAULT_MW
                              : g_params.laser_mw + 1.0f;
            laser_set_power_mw(g_params.laser_mw);
            g_state = STATE_IDLE;
            break;
        case 5: /* Set LP cutoff */
            g_params.vel_lp_fc_hz = (g_params.vel_lp_fc_hz < 1000.0f)
                                  ? 100000.0f
                                  : g_params.vel_lp_fc_hz / 10.0f;
            g_state = STATE_IDLE;
            break;
        case 6: /* IMU compensate toggle */
            g_params.imu_compensate = !g_params.imu_compensate;
            g_state = STATE_IDLE;
            break;
        case 7: /* FFT size */
            g_params.fft_size_log2 = (g_params.fft_size_log2 >= 12) ? 8
                                  : g_params.fft_size_log2 + 1;
            g_state = STATE_IDLE;
            break;
        case 8: /* BLE stream */
            g_state = STATE_LOG_STREAM;
            break;
        case 9: /* Back */
            g_state = STATE_IDLE;
            break;
        }
    } else if (g_state == STATE_CALIBRATE) {
        g_state = STATE_IDLE;
    }
}

/* ── Calibrate ──────────────────────────────────────────── */
static void run_calibrate(void)
{
    /* Acquire a static-target block, measure DC offset & amplitude */
    static uint32_t cal_start = 0;
    if (cal_start == 0) cal_start = HAL_GetTick();

    /* Wait for one block, measure baseline */
    if (adc_block_ready) {
        adc_block_ready = 0;
        interferometer_update_baseline(&g_iq);
        display_lissajous(&g_iq);
    }

    if (HAL_GetTick() - cal_start > 3000) {
        cal_start = 0;
        g_state = STATE_IDLE;
    }
}

/* ── Measure ────────────────────────────────────────────── */
static void run_measure(void)
{
    if (!laser_safety_check()) {
        g_state = STATE_FAULT;
        return;
    }

    /* Arm dual ADC DMA */
    HAL_ADCEx_MultiModeStart_DMA(&hadc1, (uint32_t *)adc1_buf, CONFIG_ADC_BLOCK_SAMPLES);

    if (adc_block_ready) {
        adc_block_ready = 0;

        /* Copy DMA buffers into I/Q block */
        for (uint32_t i = 0; i < CONFIG_ADC_BLOCK_SAMPLES; i++) {
            g_iq.i[i] = (int16_t)adc1_buf[i] - 2048;
            g_iq.q[i] = (int16_t)adc2_buf[i] - 2048;
        }
        g_iq.n = CONFIG_ADC_BLOCK_SAMPLES;

        /* Process interferometer → phase, displacement, velocity */
        interferometer_process(&g_iq, &g_phase);

        /* IMU self-motion compensation */
        if (g_params.imu_compensate) {
            imu_sample_t imu;
            imu_read(&imu);
            float sway = imu_compensate_velocity(&imu, (float)HAL_GetTick());
            for (uint32_t i = 0; i < g_phase.n; i++) {
                g_phase.vel_mms[i] -= sway;
            }
        }

        /* Log to SD */
        if (g_params.log_csv) {
            storage_log_csv(&g_phase, HAL_GetTick() - measure_start_ms);
        }
        if (g_params.log_bin) {
            storage_log_iq_bin(&g_iq, HAL_GetTick() - measure_start_ms);
        }

        /* Live display */
        display_measure_live(&g_phase, NULL);

        /* After N blocks, run FFT & go to result */
        if (HAL_GetTick() - measure_start_ms > 2000) {
            HAL_ADC_Stop_DMA(&hadc1);
            g_state = STATE_PROCESS;
        }
    }
}

/* ── Process (FFT / modal) ───────────────────────────────── */
static void run_process(void)
{
    if (g_params.run_fft) {
        dsp_fft(g_phase.vel_mms, g_phase.n, &g_fft);
        if (g_params.run_modal) {
            dsp_modal_fit(&g_fft, 1.0f, 100000.0f, &g_modal);
        }
    }

    /* Compute summary result */
    float p2p = 0.0f, vpeak = 0.0f, vrms = 0.0f, vdc = 0.0f;
    float vmin = 1e9f, vmax = -1e9f;
    for (uint32_t i = 0; i < g_phase.n; i++) {
        float d = g_phase.disp_nm[i];
        float v = g_phase.vel_mms[i];
        if (d < vmin) vmin = d;
        if (d > vmax) vmax = d;
        if (fabsf(v) > fabsf(vpeak)) vpeak = v;
        vrms += v * v;
        vdc  += v;
    }
    p2p = vmax - vmin;
    vrms = sqrtf(vrms / g_phase.n);
    vdc  = vdc / g_phase.n;

    g_result.displacement_nm = p2p;
    g_result.velocity_mms    = vpeak;
    g_result.dc_velocity_mms = vdc;
    g_result.rms_velocity_mms = vrms;
    g_result.freq_peak_hz    = g_params.run_fft ? g_fft.freq_peak_hz : 0.0f;
    g_result.thd_pct         = g_params.run_fft ? g_fft.thd_pct : 0.0f;
    g_result.fringe_count    = g_phase.last_phase / CONFIG_PHASE_WRAP_2PI;
    g_result.snr_db          = g_params.run_fft ? g_fft.snr_db : 0.0f;

    /* BLE result */
    ble_bridge_send_result(&g_result);
    if (g_params.run_fft) ble_bridge_send_fft(&g_fft);

    g_state = STATE_DISPLAY_RESULT;
}

/* ── Display result ─────────────────────────────────────── */
static void run_display_result(void)
{
    display_result(&g_result);
    HAL_Delay(100);
}

/* ── BLE stream ─────────────────────────────────────────── */
static void run_log_stream(void)
{
    if (adc_block_ready) {
        adc_block_ready = 0;
        for (uint32_t i = 0; i < CONFIG_ADC_BLOCK_SAMPLES; i++) {
            g_iq.i[i] = (int16_t)adc1_buf[i] - 2048;
            g_iq.q[i] = (int16_t)adc2_buf[i] - 2048;
        }
        g_iq.n = CONFIG_ADC_BLOCK_SAMPLES;
        interferometer_process(&g_iq, &g_phase);
        ble_bridge_send_stream(&g_phase, HAL_GetTick());
        display_measure_live(&g_phase, NULL);
    }
}

/* ── Audio listen ───────────────────────────────────────── */
static void run_audio_listen(void)
{
    if (adc_block_ready) {
        adc_block_ready = 0;
        for (uint32_t i = 0; i < CONFIG_ADC_BLOCK_SAMPLES; i++) {
            g_iq.i[i] = (int16_t)adc1_buf[i] - 2048;
            g_iq.q[i] = (int16_t)adc2_buf[i] - 2048;
        }
        g_iq.n = CONFIG_ADC_BLOCK_SAMPLES;
        interferometer_process(&g_iq, &g_phase);
        for (uint32_t i = 0; i < g_phase.n; i++) {
            audio_push_velocity(g_phase.vel_mms[i]);
        }
        display_audio(1, g_params.audio_gain, g_params.audio_shift);
    }
}

/* ── Fault ─────────────────────────────────────────────── */
static void run_fault(void)
{
    display_fault("Safety / tilt / lid");
    set_status_led(1, 0, 0);
    shutter_close();
    laser_disable();
    HAL_Delay(500);
    if (laser_safety_check()) {
        g_state = STATE_IDLE;
        laser_enable();
        shutter_open();
    }
}

/* ── BLE commands ──────────────────────────────────────── */
static void handle_ble_commands(void)
{
    ble_bridge_handle_commands(&g_params);
}

/* ── Default params ─────────────────────────────────────── */
static void default_params(void)
{
    memset(&g_params, 0, sizeof(g_params));
    g_params.laser_mw        = CONFIG_LASER_DEFAULT_MW;
    g_params.vel_lp_fc_hz    = CONFIG_VEL_LP_FC_DEFAULT_HZ;
    g_params.fft_size_log2   = CONFIG_FFT_SIZE_LOG2;
    g_params.imu_compensate  = 1;
    g_params.audio_enable    = 0;
    g_params.audio_gain      = CONFIG_AUDIO_GAIN_DEFAULT;
    g_params.audio_shift     = CONFIG_AUDIO_SHIFT_DEFAULT;
    g_params.log_csv         = 1;
    g_params.log_bin         = 0;
    g_params.ble_stream      = 0;
    g_params.run_fft         = 1;
    g_params.run_modal       = 0;
    g_params.target_freq_hz  = 0.0f;
}

/* ── Status LED ─────────────────────────────────────────── */
static void set_status_led(uint8_t r, uint8_t g, uint8_t b)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_1, r ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_2, g ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_3, b ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ── ADC DMA complete callback ──────────────────────────── */
void HAL_ADCEx_ConvCpltCallback(ADC_HandleTypeDef *h)
{
    if (h->Instance == ADC1) {
        adc_block_ready = 1;
    }
}

/* ── Button EXTI ────────────────────────────────────────── */
void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    uint32_t now = HAL_GetTick();
    if (pin == GPIO_PIN_15) {       /* Button A on PB15 */
        if (now - last_btn_a > 200) {
            btn_a_flag = 1;
            last_btn_a = now;
        }
    } else if (pin == GPIO_PIN_0) { /* Button B on PC0 */
        if (now - last_btn_b > 200) {
            btn_b_flag = 1;
            last_btn_b = now;
        }
    } else if (pin == GPIO_PIN_14) { /* Reed interlock on PB14 */
        shutter_close();
        laser_disable();
        g_state = STATE_FAULT;
    }
}

/* ── Peripheral init (CubeMX-style) ─────────────────────── */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_LSE;
    osc.HSEState = RCC_HSE_ON;
    osc.LSEState = RCC_LSE_ON;
    osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 6;
    osc.PLL.PLLN = 85;
    osc.PLL.PLLP = RCC_PLLP_DIV2;
    osc.PLL.PLLQ = 8;
    osc.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);

    HAL_RCC_MCOConfig(RCC_MCO1, RCC_MCO1SOURCE_PLLCLK, RCC_MCODIV_4);
}

static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef gp = {0};

    /* ADC pins PA0, PA1 */
    gp.Pin = GPIO_PIN_0 | GPIO_PIN_1;
    gp.Mode = GPIO_MODE_ANALOG_ADC_CONTROL;
    HAL_GPIO_Init(GPIOA, &gp);

    /* UART2 TX/RX: PA2, PA3 */
    gp.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    gp.Mode = GPIO_MODE_AF_PP;
    gp.Pull = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    gp.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &gp);

    /* Laser EN PA5, DAC PA4 */
    gp.Pin = GPIO_PIN_5;
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &gp);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

    /* I2C1 PB6 SCL, PB7 SDA */
    gp.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    gp.Mode = GPIO_MODE_AF_OD;
    gp.Pull = GPIO_PULLUP;
    gp.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &gp);

    /* SPI2 PB10/12/13, PB11 MISO */
    gp.Pin = GPIO_PIN_10 | GPIO_PIN_12 | GPIO_PIN_13;
    gp.Mode = GPIO_MODE_AF_PP;
    gp.Alternate = GPIO_AF5_SPI2;
    HAL_GPIO_Init(GPIOB, &gp);
    gp.Pin = GPIO_PIN_11;
    gp.Mode = GPIO_MODE_AF_PP;
    gp.Alternate = GPIO_AF5_SPI2;
    HAL_GPIO_Init(GPIOB, &gp);

    /* I2S2 PA8/9/10 */
    gp.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    gp.Mode = GPIO_MODE_AF_PP;
    gp.Alternate = GPIO_AF5_SPI2; /* shared I2S on SPI2 */
    HAL_GPIO_Init(GPIOA, &gp);

    /* Reed PB14 (input IRQ), Button A PB15 */
    gp.Pin = GPIO_PIN_14 | GPIO_PIN_15;
    gp.Mode = GPIO_MODE_IT_RISING;
    gp.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOB, &gp);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

    /* Button B PC0 */
    gp.Pin = GPIO_PIN_0;
    gp.Mode = GPIO_MODE_IT_RISING;
    gp.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOC, &gp);
    HAL_NVIC_SetPriority(EXTI0_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);

    /* RGB LED PC1/2/3 */
    gp.Pin = GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3;
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOC, &gp);

    /* DS18B20 PC8 (open-drain for 1-Wire) */
    gp.Pin = GPIO_PIN_8;
    gp.Mode = GPIO_MODE_OUTPUT_OD;
    gp.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &gp);
}

static void MX_ADC1_Init(void)
{
    __HAL_RCC_ADC12_CLK_ENABLE();
    ADC_MultiModeTypeDef multimode = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = ENABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DMAContinuousRequests = ENABLE;
    HAL_ADC_Init(&hadc1);

    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_1;  /* PA0 = I */
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
    ch.SingleDiff = ADC_SINGLE_ENDED;
    HAL_ADC_ConfigChannel(&hadc1, &ch);

    multimode.Mode = ADC_DUALMODE_REGSIMULT;
    multimode.DMAAccessMode = ADC_DMAACCESSMODE_12_2;
    multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_5CYCLES;
    HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode);
}

static void MX_ADC2_Init(void)
{
    hadc2.Instance = ADC2;
    hadc2.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc2.Init.Resolution = ADC_RESOLUTION_12B;
    hadc2.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc2.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc2.Init.ContinuousConvMode = ENABLE;
    hadc2.Init.NbrOfConversion = 1;
    hadc2.Init.DiscontinuousConvMode = DISABLE;
    hadc2.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc2.Init.DMAContinuousRequests = ENABLE;
    HAL_ADC_Init(&hadc2);

    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_2;  /* PA1 = Q */
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
    ch.SingleDiff = ADC_SINGLE_ENDED;
    HAL_ADC_ConfigChannel(&hadc2, &ch);
}

static void MX_I2C1_Init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x30A0A1FB; /* 400 kHz @ 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void MX_SPI2_Init(void)
{
    __HAL_RCC_SPI2_CLK_ENABLE();
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4;
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi2.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi2.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    HAL_SPI_Init(&hspi2);
}

static void MX_TIM3_Init(void)
{
    __HAL_RCC_TIM3_CLK_ENABLE();
    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 0;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 1700;   /* 100 kHz */
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim3);
}

static void MX_TIM8_Init(void)
{
    __HAL_RCC_TIM8_CLK_ENABLE();
    htim8.Instance = TIM8;
    htim8.Init.Prescaler = 170;
    htim8.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim8.Init.Period = 1000;   /* 1 kHz for laser PWM */
    htim8.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim8);
}

static void MX_USART2_UART_Init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();
    huart2.Instance = USART2;
    huart2.Init.BaudRate = CONFIG_BLE_UART_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    huart2.Init.OneBitSampling = UART_ONEBIT_SAMPLING_DISABLED;
    HAL_UART_Init(&huart2);
}

static void MX_I2S2_Init(void)
{
    __HAL_RCC_SPI2_CLK_ENABLE();
    hi2s2.Instance = SPI2;
    hi2s2.Init.Mode = I2S_MODE_MASTER;
    hi2s2.Init.Standard = I2S_STANDARD_PHILIPS;
    hi2s2.Init.DataFormat = I2S_DATAFORMAT_16B_EXTENDED;
    hi2s2.Init.MCLKOutput = I2S_MCLKOUTPUT_DISABLE;
    hi2s2.Init.AudioFreq = I2S_AUDIOFREQ_44K;
    hi2s2.Init.CPOL = I2S_CPOL_LOW;
    hi2s2.Init.FirstBit = I2S_FIRSTBIT_MSB;
    HAL_I2S_Init(&hi2s2);
}

/* ── IWDG watchdog (safety) ─────────────────────────────── */
IWDG_HandleTypeDef hiwdg;
void MX_IWDG_Init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Reload = 0xFFF;
    hiwdg.Init.Window = 0xFFF;
    HAL_IWDG_Init(&hiwdg);
}

/* ── Error handler ──────────────────────────────────────── */
void Error_Handler(void)
{
    while (1) {
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_1);
        HAL_Delay(200);
    }
}

/* ── HAL MSP init hooks ─────────────────────────────────── */
void HAL_ADC_MspInit(ADC_HandleTypeDef *h)
{
    if (h->Instance == ADC1) {
        __HAL_RCC_ADC12_CLK_ENABLE();
        __HAL_RCC_DMA1_CLK_ENABLE();
        static DMA_HandleTypeDef hdma_adc1;
        hdma_adc1.Instance = DMA1_Channel1;
        hdma_adc1.Init.Request = DMA_REQUEST_ADC1;
        hdma_adc1.Init.Direction = DMA_PERIPH_TO_MEMORY;
        hdma_dma1.Init.PeriphInc = DMA_PINC_DISABLE;
        hdma_adc1.Init.MemInc = DMA_MINC_ENABLE;
        hdma_adc1.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
        hdma_adc1.Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
        hdma_adc1.Init.Mode = DMA_CIRCULAR;
        hdma_adc1.Init.Priority = DMA_PRIORITY_HIGH;
        HAL_DMA_Init(&hdma_adc1);
        __HAL_LINKDMA(h, DMA_Handle, hdma_adc1);
        HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
    }
}