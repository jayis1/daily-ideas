/*
 * dent-scope / Core/Src/main.c
 * Dent Scope — Pocket Instrumented Indentation Tester
 * STM32G474RET6 application. MIT License.
 *
 * Scheduler: 500 Hz acquisition loop, 10 Hz UI/logging, 1 Hz telemetry.
 */
#include "main.h"
#include "stepper.h"
#include "loadcell.h"
#include "displacement.h"
#include "indentation.h"
#include "ds18b20.h"
#include "imu.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "safety.h"
#include "esp32_link.h"
#include "flash_store.h"
#include "database.h"

ds_status_t g_status;
ds_config_t g_cfg;

TIM_HandleTypeDef htim3;
ADC_HandleTypeDef hadc1;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1, hspi2;
UART_HandleTypeDef huart1;
IWDG_HandleTypeDef hiwdg;

static uint32_t last_500hz_ms = 0, last_10hz_ms = 0, last_1hz_ms = 0;

/* ---- GPIO init ---- */
static void gpio_init_extra(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};
    g.Pull = GPIO_NOPULL; g.Speed = GPIO_SPEED_FREQ_LOW;

    /* outputs */
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pin = HX711_SCK_PIN;   HAL_GPIO_Init(HX711_SCK_PORT, &g);
    g.Pin = HX711_RATE_PIN;  HAL_GPIO_Init(HX711_RATE_PORT, &g);
    g.Pin = STEP_IN1_PIN;    HAL_GPIO_Init(STEP_IN1_PORT, &g);
    g.Pin = STEP_IN2_PIN;    HAL_GPIO_Init(STEP_IN2_PORT, &g);
    g.Pin = STEP_IN3_PIN;    HAL_GPIO_Init(STEP_IN3_PORT, &g);
    g.Pin = STEP_IN4_PIN;    HAL_GPIO_Init(STEP_IN4_PORT, &g);
    g.Pin = STEP_EN_PIN;     HAL_GPIO_Init(STEP_EN_PORT, &g);
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_SET); /* disabled */
    g.Pin = BUZZER_PIN;      HAL_GPIO_Init(BUZZER_PORT, &g);
    g.Pin = LED_PIN;         HAL_GPIO_Init(LED_PORT, &g);
    g.Pin = OLED_CS_PIN;     HAL_GPIO_Init(OLED_CS_PORT, &g);
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
    g.Pin = SD_CS_PIN;       HAL_GPIO_Init(SD_CS_PORT, &g);
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET);
    g.Pin = OLED_DC_PIN;     HAL_GPIO_Init(OLED_DC_PORT, &g);
    g.Pin = OLED_RST_PIN;    HAL_GPIO_Init(OLED_RST_PORT, &g);
    g.Pin = IMU_CS_PIN;       HAL_GPIO_Init(IMU_CS_PORT, &g);
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_SET);
    g.Pin = ESP_RST_PIN;     HAL_GPIO_Init(ESP_RST_PORT, &g);
    g.Pin = MOTOR_BRAKE_PIN;  HAL_GPIO_Init(MOTOR_BRAKE_PORT, &g);

    /* inputs */
    g.Mode = GPIO_MODE_INPUT; g.Pull = GPIO_PULLUP;
    g.Pin = HX711_DOUT_PIN;   HAL_GPIO_Init(HX711_DOUT_PORT, &g);
    g.Pin = STALL_PIN;         HAL_GPIO_Init(STALL_PORT, &g);
    g.Pin = INTERLOCK_PIN;     HAL_GPIO_Init(INTERLOCK_PORT, &g);
    g.Pin = BTN_START_PIN|BTN_STOP_PIN|BTN_MENU_PIN; HAL_GPIO_Init(GPIOB, &g);

    /* DS18B20 1-wire pin */
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Pin = ONEWIRE_PIN;
    HAL_GPIO_Init(ONEWIRE_PORT, &g);
}

static void iwdg_init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_256;
    hiwdg.Init.Reload = 0xFFF;
    hiwdg.Init.Window = 0xFFF;
    HAL_IWDG_Init(&hiwdg);
}

/* ---- Button handling (debounced) ---- */
static void buttons_scan(void)
{
    static uint32_t db_start = 0, db_stop = 0, db_menu = 0;

    if (!HAL_GPIO_ReadPin(BTN_START_PORT, BTN_START_PIN)) {
        if (HAL_GetTick() - db_start > 200) {
            if (g_status.state == DS_IDLE) {
                if (!HAL_GPIO_ReadPin(INTERLOCK_PORT, INTERLOCK_PIN)) {
                    oled_text(0, "No tip inserted!");
                    oled_text(1, "Insert tip + retry");
                } else if (fabsf(g_status.tilt_deg) > 2.0f) {
                    oled_text(0, "Tilt too large");
                    oled_text(1, "Level the device");
                } else {
                    stepper_approach();
                    g_status.state = DS_APPROACHING;
                    g_status.t_start_ms = HAL_GetTick();
                    indentation_reset();
                    sd_open_run(g_status.point_count);
                }
            }
            db_start = HAL_GetTick();
        }
    } else db_start = HAL_GetTick();

    if (!HAL_GPIO_ReadPin(BTN_STOP_PORT, BTN_STOP_PIN)) {
        if (HAL_GetTick() - db_stop > 200) {
            if (g_status.state == DS_LOADING ||
                g_status.state == DS_HOLDING ||
                g_status.state == DS_UNLOADING) {
                stepper_retract();
                g_status.state = DS_RETRACTING;
                HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_SET);
                HAL_Delay(100);
                HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_RESET);
            }
            db_stop = HAL_GetTick();
        }
    } else db_stop = HAL_GetTick();

    if (!HAL_GPIO_ReadPin(BTN_MENU_PORT, BTN_MENU_PIN)) {
        if (HAL_GetTick() - db_menu > 200) {
            /* cycle tip type: Vickers → Berkovich → WC Ball → Vickers */
            g_cfg.tip = (tip_type_t)((g_cfg.tip + 1) % 3);
            /* update target force default per tip */
            if (g_cfg.tip == TIP_WC_BALL_1MM) g_cfg.target_force_N = 15.0f;
            else g_cfg.target_force_N = 10.0f;
            flash_save();
            db_menu = HAL_GetTick();
        }
    } else db_menu = HAL_GetTick();
}

/* ---- 500 Hz acquisition + control loop ---- */
static void run_tick_500hz(void)
{
    /* acquire force and depth */
    loadcell_read_mN();
    displacement_read_um();

    g_status.force_mN = loadcell_last_mN();
    g_status.depth_um = displacement_last_um();

    /* track peak values */
    if (g_status.force_mN > g_status.peak_force_mN)
        g_status.peak_force_mN = g_status.force_mN;
    if (g_status.depth_um > g_status.peak_depth_um)
        g_status.peak_depth_um = g_status.depth_um;

    /* stall / over-travel detection */
    if (!safety_check()) {
        stepper_emergency_stop();
        g_status.state = DS_ALARM;
        return;
    }

    /* state machine for approach / load / hold / unload */
    switch (g_status.state) {
    case DS_APPROACHING:
        /* slow approach until force > 50 mN (surface contact) */
        if (g_status.force_mN > 50.0f) {
            stepper_stop();
            stepper_hold_position(); /* maintain contact */
            g_status.state = DS_LOADING;
            g_status.peak_force_mN = g_status.force_mN;
            g_status.peak_depth_um = g_status.depth_um;
        } else {
            stepper_tick_approach();
        }
        break;

    case DS_LOADING: {
        /* force-controlled loading via stepper microstepping */
        float target_mN = g_cfg.target_force_N * 1000.0f;
        float rate_mN_per_s = g_cfg.loading_rate_Ns * 1000.0f;
        /* expected force at this time based on linear ramp */
        float elapsed_s = (HAL_GetTick() - g_status.t_start_ms) / 1000.0f;
        float expected_force = rate_mN_per_s * (elapsed_s - g_status.contact_time_s);
        if (expected_force > target_mN) expected_force = target_mN;
        /* PID on force: step down to increase force, step up to decrease */
        float error = expected_force - g_status.force_mN;
        if (error > 2.0f) stepper_step_down();      /* need more force */
        else if (error < -2.0f) stepper_step_up();  /* too much force */
        /* record P–h point */
        indentation_push(g_status.force_mN, g_status.depth_um);
        if (g_status.force_mN >= target_mN - 5.0f) {
            g_status.state = DS_HOLDING;
            g_status.hold_start_ms = HAL_GetTick();
            g_status.peak_force_mN = g_status.force_mN;
            g_status.peak_depth_um = g_status.depth_um;
        }
        break;
    }

    case DS_HOLDING:
        /* constant force hold for creep measurement */
        {
            float target_mN = g_cfg.target_force_N * 1000.0f;
            float error = target_mN - g_status.force_mN;
            if (error > 2.0f) stepper_step_down();
            else if (error < -2.0f) stepper_step_up();
            indentation_push(g_status.force_mN, g_status.depth_um);
            float hold_elapsed = (HAL_GetTick() - g_status.hold_start_ms) / 1000.0f;
            if (hold_elapsed >= g_cfg.hold_time_s) {
                g_status.state = DS_UNLOADING;
                g_status.unload_start_ms = HAL_GetTick();
                g_status.unload_start_force = g_status.force_mN;
                g_status.unload_start_depth = g_status.depth_um;
            }
        }
        break;

    case DS_UNLOADING: {
        /* force-controlled unloading at same rate */
        float rate_mN_per_s = g_cfg.loading_rate_Ns * 1000.0f;
        float unload_elapsed = (HAL_GetTick() - g_status.unload_start_ms) / 1000.0f;
        float expected_force = g_status.unload_start_force - rate_mN_per_s * unload_elapsed;
        if (expected_force < 0.0f) expected_force = 0.0f;
        float error = expected_force - g_status.force_mN;
        if (error < -2.0f) stepper_step_up();     /* reduce force */
        else if (error > 2.0f) stepper_step_down();
        indentation_push(g_status.force_mN, g_status.depth_um);
        if (g_status.force_mN < 5.0f) {
            g_status.final_depth_um = g_status.depth_um;
            stepper_retract();
            g_status.state = DS_RETRACTING;
            indentation_finalize();
            indentation_compute(&g_status);
            database_match(&g_status);
        }
        break;
    }

    case DS_RETRACTING:
        stepper_tick_retract();
        if (stepper_is_retracted()) {
            sd_close_run();
            esp32_send_result(&g_status);
            g_status.state = DS_IDLE;
            HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_SET);
            HAL_Delay(80);
            HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_RESET);
        }
        break;

    default:
        break;
    }
}

/* ---- 10 Hz: buttons, UI, SD ---- */
static void run_tick_10hz(void)
{
    buttons_scan();
    esp32_link_poll();

    /* battery voltage */
    {
        uint32_t s = 0;
        for (int i = 0; i < 8; i++) {
            ADC_ChannelConfTypeDef c = {0};
            c.Channel = ADC_CHANNEL_1; c.Rank = 1; c.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
            HAL_ADC_ConfigChannel(&hadc1, &c);
            HAL_ADC_Start(&hadc1);
            if (HAL_ADC_PollForConversion(&hadc1, 5) == HAL_OK) s += HAL_ADC_GetValue(&hadc1);
            HAL_ADC_Stop(&hadc1);
        }
        uint16_t vadc = s >> 3;
        g_status.battery_v = (vadc * 3.3f * 4.0f) / 4095.0f;
    }

    /* tilt from IMU */
    g_status.tilt_deg = imu_get_tilt_deg();

    /* SD logging at 10 Hz during test (500 Hz data decimated) */
    if (g_status.state == DS_LOADING || g_status.state == DS_HOLDING ||
        g_status.state == DS_UNLOADING) {
        sd_log_point(g_status.force_mN, g_status.depth_um,
                     g_status.state, HAL_GetTick() - g_status.t_start_ms);
        esp32_send_point(g_status.force_mN, g_status.depth_um,
                         HAL_GetTick() - g_status.t_start_ms);
    }

    /* OLED update */
    oled_draw_status(&g_status);
}

/* ---- 1 Hz: telemetry + temperature ---- */
static void run_tick_1hz(void)
{
    g_status.temp_c = ds18b20_read_temp();
    if (g_status.state == DS_IDLE && g_status.hardness_HV > 0) {
        oled_draw_results(&g_status);
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    gpio_init_extra();
    iwdg_init();

    /* peripheral inits */
    loadcell_init();
    displacement_init();
    stepper_init();
    indentation_init();
    ds18b20_init();
    imu_init();
    oled_init();
    sd_init();
    safety_init();
    esp32_link_init();
    flash_load();
    database_init();

    if (g_cfg.magic != 0x44454E54) flash_defaults(); /* "DENT" */

    g_status.state = DS_IDLE;
    g_status.tip = g_cfg.tip;
    g_status.target_force_N = g_cfg.target_force_N;
    g_status.loading_rate_Ns = g_cfg.loading_rate_Ns;
    g_status.hold_time_s = g_cfg.hold_time_s;
    g_status.poisson = g_cfg.poisson;

    oled_text(0, "Dent Scope v1.0");
    oled_text(1, "Ready. Press START.");

    while (1) {
        HAL_IWDG_Refresh(&hiwdg);
        uint32_t now = HAL_GetTick();

        if (now - last_500hz_ms >= 2) {
            last_500hz_ms = now;
            run_tick_500hz();
        }
        if (now - last_10hz_ms >= 100) {
            last_10hz_ms = now;
            run_tick_10hz();
        }
        if (now - last_1hz_ms >= 1000) {
            last_1hz_ms = now;
            run_tick_1hz();
        }
        __WFI();
    }
}

/* ---- HAL stubs ---- */
void HAL_MspInit(void) {}
void NMI_Handler(void) {}
void HardFault_Handler(void) { while (1); }
void MemManage_Handler(void) { while (1); }
void BusFault_Handler(void) { while (1); }
void UsageFault_Handler(void) { while (1); }
void SVC_Handler(void) {}
void DebugMon_Handler(void) {}
void PendSV_Handler(void) {}
void SysTick_Handler(void) { HAL_IncTick(); }

void Error_Handler(void) {
    while (1) { HAL_GPIO_TogglePin(LED_PORT, LED_PIN); HAL_Delay(50); }
}

void SystemClock_Config(void)
{
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    o.HSEState = RCC_HSE_ON;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = 6; o.PLL.PLLN = 85; o.PLL.PLLP = 7; o.PLL.PLLQ = 2; o.PLL.PLLR = 2;
    if (HAL_RCC_OscConfig(&o) != HAL_OK) Error_Handler();
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV1;
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&c, FLASH_LATENCY_4) != HAL_OK) Error_Handler();
}