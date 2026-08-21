/*
 * main.c — QCM Halo main application
 * STM32G474RET6
 *
 * Pocket QCM-D (Quartz Crystal Microbalance with Dissipation) instrument.
 * State machine: BOOT → IDLE → MENU → CALIBRATE → MEASURE → RINGDOWN →
 *                PROCESS → DISPLAY_RESULT → LOG_STREAM → EXPERIMENT
 */

#include "main.h"
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "config.h"
#include "qcm_driver.h"
#include "dissipation.h"
#include "sauerbrey.h"
#include "voigt.h"
#include "overtone.h"
#include "temperature.h"
#include "liquid.h"
#include "display.h"
#include "storage.h"
#include "ble_bridge.h"
#include "onewire.h"
#include "power.h"
#include "i2c_util.h"

/* ── Global Handles ─────────────────────────────────────── */
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1;
SPI_HandleTypeDef hspi3;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim4;
UART_HandleTypeDef huart2;

/* ── Global State ───────────────────────────────────────── */
volatile device_state_t g_state = STATE_BOOT;
acq_params_t g_params;
static overtone_sweep_t g_sweep;
static voigt_params_t g_voigt;
static kinetic_result_t g_kinetic;

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
static void MX_SPI1_Init(void);
static void MX_SPI3_Init(void);
static void MX_TIM1_Init(void);
static void MX_TIM2_Init(void);
static void MX_TIM4_Init(void);
static void MX_USART2_UART_Init(void);

static void run_boot(void);
static void run_idle(void);
static void run_menu(void);
static void run_calibrate(void);
static void run_measure(void);
static void run_process(void);
static void run_display_result(void);
static void run_log_stream(void);
static void run_experiment(void);
static void handle_ble_commands(void);
static void set_status_led(uint8_t r, uint8_t g, uint8_t b);
static void default_params(void);
static void button_a_handler(void);
static void button_b_handler(void);

/* ── Main ──────────────────────────────────────────────── */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_ADC2_Init();
    MX_I2C1_Init();
    MX_SPI1_Init();
    MX_SPI3_Init();
    MX_TIM1_Init();
    MX_TIM2_Init();
    MX_TIM4_Init();
    MX_USART2_UART_Init();

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
        case STATE_EXPERIMENT:
            run_experiment();
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
    }
}

/* ── Boot sequence ──────────────────────────────────────── */
static void run_boot(void)
{
    display_init();
    display_boot("QCM Halo v1.0");

    /* Initialize peripherals */
    if (i2c_util_init() != 0) {
        display_boot("I2C FAIL");
        HAL_Delay(2000);
    }

    /* Si5351A clock generator */
    if (si5351_init() != 0) {
        display_boot("Si5351 FAIL");
        HAL_Delay(2000);
    }

    /* Temperature control */
    temperature_init();

    /* Liquid handling */
    pump_init();
    valve_init();

    /* Storage */
    storage_init();

    /* BLE bridge */
    ble_bridge_init();

    /* Load saved parameters */
    storage_load_params(&g_params);

    /* Set default temperature */
    if (g_params.target_temp > 0) {
        temperature_set_target(g_params.target_temp);
        temperature_enable();
    }

    display_boot("Ready!");
    HAL_Delay(1000);
    set_status_led(0, 1, 0); /* green = ready */
}

/* ── Idle ──────────────────────────────────────────────── */
static void run_idle(void)
{
    float temp = temperature_read();
    float vbat = power_read_battery_mv();

    display_idle(temp, vbat, g_params.channel);

    /* Periodic temperature PID */
    if (g_params.target_temp > 0) {
        temperature_pid_step(g_params.target_temp);
    }

    HAL_Delay(100);
}

/* ── Menu ───────────────────────────────────────────────── */
static uint8_t menu_item = 0;
static const char *menu_items[] = {
    "Single Measure",
    "Overtone Sweep",
    "Calibrate",
    "Experiment",
    "Set Temperature",
    "Set Pump Rate",
    "Set Valve",
    "Voigt Fit",
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
    /* Button A = navigate / change state */
    if (g_state == STATE_IDLE) {
        g_state = STATE_MENU;
        menu_item = 0;
    } else if (g_state == STATE_MENU) {
        menu_item = (menu_item + 1) % MENU_COUNT;
    } else if (g_state == STATE_DISPLAY_RESULT) {
        g_state = STATE_IDLE;
    } else if (g_state == STATE_LOG_STREAM) {
        g_state = STATE_IDLE;
    }
}

static void button_b_handler(void)
{
    /* Button B = select */
    if (g_state == STATE_MENU) {
        switch (menu_item) {
        case 0: /* Single Measure */
            g_params.run_overtone_sweep = 0;
            g_state = STATE_MEASURE;
            break;
        case 1: /* Overtone Sweep */
            g_params.run_overtone_sweep = 1;
            g_state = STATE_MEASURE;
            break;
        case 2: /* Calibrate */
            g_state = STATE_CALIBRATE;
            break;
        case 3: /* Experiment */
            g_state = STATE_EXPERIMENT;
            measure_start_ms = HAL_GetTick();
            break;
        case 4: /* Set Temperature */
            g_params.target_temp = (g_params.target_temp == 0) ? TEC_TEMP_DEFAULT : 0;
            if (g_params.target_temp > 0) {
                temperature_set_target(g_params.target_temp);
                temperature_enable();
            } else {
                temperature_disable();
            }
            g_state = STATE_IDLE;
            break;
        case 5: /* Set Pump Rate */
            g_params.pump_rate = (g_params.pump_rate == 0) ? 2.0f : 0;
            pump_set_rate(g_params.pump_rate);
            g_state = STATE_IDLE;
            break;
        case 6: /* Set Valve */
            g_params.valve_pos = (g_params.valve_pos + 1) % 6;
            valve_set_position(g_params.valve_pos);
            g_state = STATE_IDLE;
            break;
        case 7: /* Voigt Fit toggle */
            g_params.voigt_fit = !g_params.voigt_fit;
            g_state = STATE_IDLE;
            break;
        case 8: /* BLE Stream */
            g_state = STATE_LOG_STREAM;
            break;
        case 9: /* Back */
            g_state = STATE_IDLE;
            break;
        }
    } else if (g_state == STATE_MEASURE || g_state == STATE_EXPERIMENT) {
        /* Stop measurement */
        g_state = STATE_IDLE;
        pump_stop();
    }
}

/* ── Calibration ────────────────────────────────────────── */
static void run_calibrate(void)
{
    display_boot("Calibrating...");
    set_status_led(1, 0, 0); /* red = active */

    /* Measure baseline f and D at all overtones in air (or buffer) */
    for (uint8_t ch = 0; ch < QCM_CHANNELS; ch++) {
        for (uint8_t ov = 0; ov < QCM_OVERtones; ov++) {
            float f = qcm_measure_frequency(ch, QCM_GATE_TIME_MS);
            float f0 = overtone_freq(QCM_FUNDAMENTAL_HZ, ov);

            /* Quick ring-down for D baseline */
            static uint16_t rd_buf[RINGDOWN_SAMPLES];
            qcm_capture_ringdown(ch, rd_buf, RINGDOWN_SAMPLES);
            float d = dissipation_quick(rd_buf, RINGDOWN_SAMPLES,
                                        (float)RINGDOWN_RATE_HZ, f0);

            qcm_set_baseline(ch, ov, f, d);

            char msg[32];
            snprintf(msg, sizeof(msg), "Ch%d n=%d f=%.1f", ch + 1,
                     overtone_multipliers[ov], f);
            display_boot(msg);
            HAL_Delay(200);
        }
    }

    storage_save_params(&g_params);
    display_boot("Cal Done!");
    HAL_Delay(1000);
    set_status_led(0, 1, 0);
    g_state = STATE_IDLE;
}

/* ── Measurement ────────────────────────────────────────── */
static void run_measure(void)
{
    uint32_t now = HAL_GetTick();
    float temp = temperature_read();

    set_status_led(0, 0, 1); /* blue = measuring */

    if (g_params.run_overtone_sweep) {
        /* Full overtone sweep */
        if (overtone_sweep(g_params.channel, temp, &g_sweep) == 0) {
            g_state = STATE_PROCESS;
        } else {
            display_error("Sweep failed");
            HAL_Delay(2000);
            g_state = STATE_IDLE;
        }
    } else {
        /* Single overtone measurement */
        qcm_result_t r = qcm_measure(g_params.channel, 0, temp, 1, g_params.voigt_fit);
        display_measure_live(&r, 0);

        /* Log to SD */
        storage_log_result(&r);

        /* BLE stream */
        ble_send_result(&r);

        /* Auto-repeat based on interval */
        last_measure_ms = now;
        if (g_params.measure_interval_ms > 0) {
            while ((HAL_GetTick() - last_measure_ms) < g_params.measure_interval_ms) {
                HAL_Delay(10);
                handle_ble_commands();
            }
        } else {
            g_state = STATE_DISPLAY_RESULT;
        }
    }
}

/* ── Process (Voigt fitting) ────────────────────────────── */
static void run_process(void)
{
    display_boot("Fitting Voigt...");
    set_status_led(1, 0, 1); /* magenta = processing */

    /* Compute Δf/ΔD relative to baseline */
    float df[QCM_OVERtones], dd[QCM_OVERtones], fn[QCM_OVERtones];
    float f0_base, d0_base;

    for (uint8_t i = 0; i < QCM_OVERtones; i++) {
        qcm_get_baseline(g_params.channel, i, &f0_base, &d0_base);
        df[i] = g_sweep.delta_f[i];
        dd[i] = g_sweep.delta_d[i];
        fn[i] = g_sweep.freq[i];
    }

    if (g_params.voigt_fit) {
        /* Need liquid properties for Voigt model */
        float rho_l = 1000.0f; /* water */
        float eta_l = 0.001f;  /* Pa·s water */
        float rho_eta[2] = {rho_l, eta_l};

        g_voigt = voigt_fit(fn, df, dd, QCM_OVERtones, rho_eta,
                            QCM_FUNDAMENTAL_HZ, QUARTZ_DENSITY, QUARTZ_SHEAR_MOD);

        display_voigt_result(&g_voigt);
    } else {
        /* Sauerbrey only — use 3rd overtone (index 1) as standard */
        float df3 = g_sweep.delta_f[1];
        float dd3 = g_sweep.delta_d[1];
        float f03 = overtone_freq(QCM_FUNDAMENTAL_HZ, 1);

        display_overtone_table(&g_sweep);

        if (is_sauerbrey_valid(dd3, df3)) {
            /* Rigid film — Sauerbrey valid */
            float mass = sauerbrey_mass(df3, f03, SAUERBREY_AREA_CM2);
            char msg[48];
            snprintf(msg, sizeof(msg), "Sauerbrey: %.1f ng/cm2", mass);
            display_boot(msg);
        } else {
            display_boot("Soft film — use Voigt");
        }
    }

    /* Log sweep */
    storage_log_sweep(&g_sweep);
    ble_send_sweep(&g_sweep);
    if (g_params.voigt_fit) {
        ble_send_voigt(&g_voigt);
    }

    HAL_Delay(2000);
    g_state = STATE_DISPLAY_RESULT;
}

/* ── Display Result ─────────────────────────────────────── */
static void run_display_result(void)
{
    if (g_params.run_overtone_sweep) {
        display_overtone_table(&g_sweep);
    }
    /* Otherwise the live display was already shown */
    HAL_Delay(100);
}

/* ── BLE Log Stream ─────────────────────────────────────── */
static void run_log_stream(void)
{
    uint32_t now = HAL_GetTick();
    if ((now - last_measure_ms) >= 1000) { /* 1 Hz streaming */
        float temp = temperature_read();
        qcm_result_t r = qcm_measure(g_params.channel, 1, temp, 1, 0);
        ble_send_result(&r);
        storage_log_result(&r);
        display_measure_live(&r, (now - measure_start_ms) / 1000.0f);
        last_measure_ms = now;
    }
    HAL_Delay(50);
}

/* ── Experiment (binding kinetics) ──────────────────────── */
static void run_experiment(void)
{
    uint32_t now = HAL_GetTick();
    float elapsed = (now - measure_start_ms) / 1000.0f;

    if (elapsed >= g_params.duration_s) {
        /* Analyze kinetics */
        /* TODO: fit 1:1 Langmuir binding model to Δf time series */
        g_state = STATE_IDLE;
        set_status_led(0, 1, 0);
        return;
    }

    /* Continuous measurement at 1 Hz */
    if ((now - last_measure_ms) >= 1000) {
        float temp = temperature_read();
        qcm_result_t r = qcm_measure(g_params.channel, 1, temp, 0, 0);
        display_measure_live(&r, elapsed);
        ble_send_result(&r);
        storage_log_result(&r);
        last_measure_ms = now;
    }

    HAL_Delay(50);
}

/* ── BLE command handler ────────────────────────────────── */
static void handle_ble_commands(void)
{
    acq_params_t p;
    ble_cmd_t cmd = ble_get_command(&p);

    switch (cmd) {
    case BLE_CMD_START_MEASURE:
        g_params = p;
        g_state = STATE_MEASURE;
        break;
    case BLE_CMD_STOP:
        g_state = STATE_IDLE;
        pump_stop();
        break;
    case BLE_CMD_SET_CHANNEL:
        g_params.channel = p.channel;
        break;
    case BLE_CMD_SET_OVERTONE:
        g_params.overtone = p.overtone;
        break;
    case BLE_CMD_SET_TEMP:
        g_params.target_temp = p.target_temp;
        if (p.target_temp > 0) {
            temperature_set_target(p.target_temp);
            temperature_enable();
        } else {
            temperature_disable();
        }
        break;
    case BLE_CMD_SET_PUMP:
        g_params.pump_rate = p.pump_rate;
        pump_set_rate(p.pump_rate);
        break;
    case BLE_CMD_SET_VALVE:
        g_params.valve_pos = p.valve_pos;
        valve_set_position(p.valve_pos);
        break;
    case BLE_CMD_CALIBRATE:
        g_state = STATE_CALIBRATE;
        break;
    case BLE_CMD_START_EXPERIMENT:
        g_params = p;
        g_state = STATE_EXPERIMENT;
        measure_start_ms = HAL_GetTick();
        break;
    case BLE_CMD_GET_STATUS: {
        float temp = temperature_read();
        float vbat = power_read_battery_mv();
        ble_send_status(temp, vbat,
                        g_state == STATE_IDLE ? "IDLE" : "BUSY");
        break;
    }
    case BLE_CMD_SET_PARAMS:
        g_params = p;
        storage_save_params(&g_params);
        break;
    default:
        break;
    }
}

/* ── Defaults ───────────────────────────────────────────── */
static void default_params(void)
{
    memset(&g_params, 0, sizeof(g_params));
    g_params.channel = 0;
    g_params.overtone = 1;        /* 3rd overtone by default */
    g_params.run_overtone_sweep = 0;
    g_params.target_temp = 25.0f;
    g_params.pump_rate = 0;
    g_params.valve_pos = 0;
    g_params.measure_interval_ms = 1000;
    g_params.duration_s = 600;
    g_params.voigt_fit = 0;
}

/* ── Status LED ─────────────────────────────────────────── */
static void set_status_led(uint8_t r, uint8_t g, uint8_t b)
{
    HAL_GPIO_WritePin(LED_R_PORT, LED_R_PIN, r ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_G_PORT, LED_G_PIN, g ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_B_PORT, LED_B_PIN, b ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ── GPIO button interrupt ──────────────────────────────── */
void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    uint32_t now = HAL_GetTick();
    if (pin == BTN_A_PIN) {
        if (now - last_btn_a > 200) {
            btn_a_flag = 1;
            last_btn_a = now;
        }
    } else if (pin == BTN_B_PIN) {
        if (now - last_btn_b > 200) {
            btn_b_flag = 1;
            last_btn_b = now;
        }
    }
}

/* ── Error handler ──────────────────────────────────────── */
void Error_Handler(void)
{
    while (1) {
        HAL_GPIO_TogglePin(LED_R_PORT, LED_R_PIN);
        HAL_Delay(200);
    }
}

/* ═══════════════════════════════════════════════════════════
 *  HAL initialization (abridged — CubeMX generates full)
 * ═══════════════════════════════════════════════════════════ */

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 1;
    osc.PLL.PLLN = 42;
    osc.PLL.PLLP = RCC_PLLP_DIV7;
    osc.PLL.PLLQ = RCC_PLLQ_DIV2;
    osc.PLL.PLLR = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) Error_Handler();

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4) != HAL_OK) Error_Handler();
}

static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    GPIO_InitTypeDef gp = {0};

    /* Buttons (input + EXTI) */
    gp.Mode = GPIO_MODE_IT_FALLING;
    gp.Pull = GPIO_PULLUP;
    gp.Pin = BTN_A_PIN | BTN_B_PIN;
    HAL_GPIO_Init(GPIOB, &gp);

    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

    /* LEDs (output) */
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_LOW;
    gp.Pin = LED_R_PIN | LED_G_PIN | LED_B_PIN;
    HAL_GPIO_Init(GPIOB, &gp);

    /* Control pins */
    gp.Pin = TXRX_SW_PIN | CH1_SEL_PIN | CH2_SEL_PIN;
    HAL_GPIO_Init(GPIOA, &gp);

    gp.Pin = TEC_EN_PIN | VALVE_A_PIN | VALVE_B_PIN | VALVE_C_PIN;
    HAL_GPIO_Init(GPIOB, &gp);

    gp.Pin = RINGDOWN_TRIG_PIN;
    HAL_GPIO_Init(GPIOD, &gp);

    /* Reed interlock */
    gp.Mode = GPIO_MODE_INPUT;
    gp.Pull = GPIO_PULLUP;
    gp.Pin = REED_PIN;
    HAL_GPIO_Init(GPIOC, &gp);

    /* SD detect */
    gp.Pin = SD_DETECT_PIN;
    HAL_GPIO_Init(GPIOC, &gp);

    /* CS pins (high) */
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_PULLUP;
    gp.Pin = FLASH_CS_PIN;
    HAL_GPIO_Init(GPIOA, &gp);
    HAL_GPIO_WritePin(FLASH_CS_PORT, FLASH_CS_PIN, GPIO_PIN_SET);

    gp.Pin = SD_CS_PIN;
    HAL_GPIO_Init(GPIOC, &gp);
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET);
}

static void MX_ADC1_Init(void)
{
    __HAL_RCC_ADC12_CLK_ENABLE();
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV8;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.OversamplingMode = ENABLE;
    hadc1.Init.Oversampling.Ratio = 16;
    HAL_ADC_Init(&hadc1);
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
}

static void MX_ADC2_Init(void)
{
    hadc2.Instance = ADC2;
    hadc2.Init = hadc1.Init;
    HAL_ADC_Init(&hadc2);
    HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);
}

static void MX_I2C1_Init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10909CEC; /* 400 kHz at 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void MX_SPI1_Init(void)
{
    __HAL_RCC_SPI1_CLK_ENABLE();
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi1);
}

static void MX_SPI3_Init(void)
{
    __HAL_RCC_SPI3_CLK_ENABLE();
    hspi3.Instance = SPI3;
    hspi3.Init = hspi1.Init;
    hspi3.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
    HAL_SPI_Init(&hspi3);
}

static void MX_TIM1_Init(void)
{
    __HAL_RCC_TIM1_CLK_ENABLE();
    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 0;
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = 170 - 1; /* 1 MHz at 170 MHz */
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim1);
}

static void MX_TIM2_Init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 170 - 1; /* 1 MHz tick */
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 0xFFFFFFFF;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_IC_Init(&htim2);
}

static void MX_TIM4_Init(void)
{
    __HAL_RCC_TIM4_CLK_ENABLE();
    htim4.Instance = TIM4;
    htim4.Init.Prescaler = 1700 - 1; /* 100 kHz tick */
    htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim4.Init.Period = TEC_PWM_HZ ? (100000 / TEC_PWM_HZ) - 1 : 4999;
    htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim4);
}

static void MX_USART2_UART_Init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();
    huart2.Instance = USART2;
    huart2.Init.BaudRate = BLE_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart2);
}