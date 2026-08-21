/*
 * main.c — Fluor Cast main application
 * STM32G474RET6
 *
 * Pocket spectrofluorometer with EEM capability.
 * State machine: IDLE → MENU → PREVIEW → ACQUIRE → EEM_SCAN → PROCESS → RESULT → LOG
 */

#include "main.h"
#include <string.h>
#include <stdio.h>
#include "config.h"
#include "ccd_driver.h"
#include "led_wheel.h"
#include "fluorometer.h"
#include "eem.h"
#include "library.h"
#include "display.h"
#include "storage.h"
#include "ble_bridge.h"
#include "onewire.h"
#include "power.h"

/* ── Global Handles ─────────────────────────────────────── */
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
UART_HandleTypeDef huart3;

/* ── Global State ──────────────────────────────────────── */
volatile device_state_t g_state = STATE_IDLE;
acq_params_t g_params;

/* Current EEM and classification result */
static eem_t g_eem;
static classify_result_t g_result;

/* Button debounce */
static uint32_t last_button_press = 0;
static volatile uint8_t button_flag = 0;

/* ── Forward declarations ──────────────────────────────── */
static void run_idle(void);
static void run_menu(void);
static void run_preview(void);
static void run_acquire(void);
static void run_eem_scan(void);
static void run_process(void);
static void run_display_result(void);
static void run_log_stream(void);
static void run_calibrate(void);
static void handle_ble_commands(void);
static void set_status_led(uint8_t r, uint8_t g, uint8_t b);
static void default_params(void);

/* ── Main ──────────────────────────────────────────────── */
int main(void)
{
    /* HAL init */
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_ADC2_Init();
    MX_I2C1_Init();
    MX_SPI1_Init();
    MX_TIM2_Init();
    MX_TIM3_Init();
    MX_USART3_UART_Init();

    /* Default acquisition parameters */
    default_params();

    /* Initialize subsystems */
    display_init();
    display_clear();
    display_text(2, 0, "Fluor Cast v1.0", FONT_MED);
    display_text(2, 16, "Initializing...", FONT_SMALL);
    display_flush();

    power_init();
    ow_init();
    ccd_init();
    led_wheel_init();
    fluorometer_init();
    eem_init();
    library_init();
    ble_bridge_init();

    /* Try to init SD card */
    int sd_ok = storage_init();

    /* Home the LED wheel */
    display_text(2, 28, "Homing wheel...", FONT_SMALL);
    display_flush();
    led_wheel_home();

    /* Splash screen */
    display_clear();
    display_text(0, 0, "Fluor Cast v1.0", FONT_MED);
    display_text(0, 16, "Pocket EEM", FONT_SMALL);
    display_text(0, 26, "Spectrofluorometer", FONT_SMALL);
    if (sd_ok == 0) {
        display_text(0, 40, "SD: OK", FONT_SMALL);
    } else {
        display_text(0, 40, "SD: NONE", FONT_SMALL);
    }
    float v = power_battery_voltage();
    int pct = power_battery_pct();
    display_printf(0, 52, "BAT: %.1fV %d%%", v, pct);
    display_flush();

    HAL_Delay(2000);

    g_state = STATE_IDLE;

    /* ── Main Loop ───────────────────────────────────── */
    while (1) {
        /* Check for BLE commands */
        handle_ble_commands();

        /* Check button press */
        if (button_flag) {
            button_flag = 0;
            uint32_t now = HAL_GetTick();
            if (now - last_button_press > 300) {
                last_button_press = now;
                /* Button advances state */
                switch (g_state) {
                case STATE_IDLE:    g_state = STATE_MENU; break;
                case STATE_MENU:     g_state = STATE_PREVIEW; break;
                case STATE_PREVIEW: g_state = STATE_ACQUIRE; break;
                case STATE_DISPLAY_RESULT: g_state = STATE_IDLE; break;
                default: break;
                }
            }
        }

        /* State machine */
        switch (g_state) {
        case STATE_IDLE:           run_idle(); break;
        case STATE_MENU:           run_menu(); break;
        case STATE_PREVIEW:        run_preview(); break;
        case STATE_ACQUIRE:        run_acquire(); break;
        case STATE_EEM_SCAN:       run_eem_scan(); break;
        case STATE_PROCESS:        run_process(); break;
        case STATE_DISPLAY_RESULT: run_display_result(); break;
        case STATE_LOG_STREAM:     run_log_stream(); break;
        case STATE_CALIBRATE:      run_calibrate(); break;
        case STATE_ERROR:          g_state = STATE_IDLE; break;
        }

        /* Low power if idle for a while */
        if (g_state == STATE_IDLE) {
            static uint32_t last_activity = 0;
            uint32_t now = HAL_GetTick();
            if (now - last_activity > 60000) {
                display_sleep();
                power_low_power();
                /* Wake on button interrupt */
                if (button_flag) {
                    power_wake();
                    display_wake();
                    last_activity = now;
                }
            } else if (button_flag == 0) {
                last_activity = now;
            }
        }
    }
}

/* ── State Handlers ────────────────────────────────────── */

static void run_idle(void)
{
    static uint32_t last_update = 0;
    uint32_t now = HAL_GetTick();
    if (now - last_update < 500) return;
    last_update = now;

    display_clear();
    display_text(0, 0, "Fluor Cast", FONT_MED);
    display_text(0, 12, "Ready", FONT_SMALL);
    display_printf(0, 24, "BAT: %d%%", power_battery_pct());
    float temp;
    if (ds18b20_read_temp(&temp) == 0) {
        display_printf(0, 34, "Temp: %.1fC", temp);
    }
    if (ble_bridge_connected()) {
        display_text(0, 46, "BLE: Connected", FONT_SMALL);
        set_status_led(0, 1, 0);
    } else {
        display_text(0, 46, "BLE: Off", FONT_SMALL);
        set_status_led(0, 0, 1);
    }
    display_text(0, 56, "[BTN] Menu", FONT_SMALL);
    display_flush();
}

static void run_menu(void)
{
    static int menu_idx = 0;
    static uint32_t last_update = 0;
    uint32_t now = HAL_GetTick();
    if (now - last_update < 200) return;
    last_update = now;

    display_clear();
    display_text(0, 0, "== MENU ==", FONT_MED);
    const char *items[] = {
        "1. Quick Scan",
        "2. Full EEM",
        "3. Calibrate",
        "4. Settings",
        "5. Library"
    };
    for (int i = 0; i < 5; i++) {
        if (i == menu_idx) {
            display_fill_rect(0, 14 + i * 10, DISP_W, 9, 1);
            display_text(2, 14 + i * 10, items[i], FONT_SMALL);
        } else {
            display_text(2, 14 + i * 10, items[i], FONT_SMALL);
        }
    }
    display_text(0, 56, "BTN=select", FONT_SMALL);
    display_flush();
}

static void run_preview(void)
{
    /* Quick single-wavelength preview using 365nm LED */
    display_clear();
    display_text(0, 0, "Preview 365nm", FONT_MED);
    display_text(0, 12, "Measuring...", FONT_SMALL);
    display_flush();

    fluor_result_t result;
    if (fluorometer_measure(EX_365NM, &g_params, &result) == 0) {
        display_clear();
        display_text(0, 0, "Preview 365nm", FONT_SMALL);
        display_printf(0, 10, "Peak: %.0fnm", result.peak_wl);
        display_printf(0, 20, "Int: %d", result.peak_intensity);
        display_printf(0, 30, "SNR: %.1f", result.snr);
        display_spectrum(result.emission.pixels, CCD_PIXELS, 64);
        display_text(0, 54, "BTN=Full EEM", FONT_SMALL);
        display_flush();
    } else {
        display_clear();
        display_text(0, 0, "Measure error!", FONT_SMALL);
        display_text(0, 10, "Check cuvette", FONT_SMALL);
        display_flush();
        HAL_Delay(2000);
        g_state = STATE_IDLE;
    }
}

static void run_acquire(void)
{
    /* Start full EEM scan */
    g_state = STATE_EEM_SCAN;
}

static void run_eem_scan(void)
{
    uint32_t start = HAL_GetTick();

    display_clear();
    display_text(0, 0, "EEM Scanning", FONT_MED);
    display_text(0, 14, "Please wait...", FONT_SMALL);
    display_flush();

    /* Acquire full EEM */
    int rc = eem_acquire(&g_params, &g_eem);
    if (rc != 0) {
        display_clear();
        display_text(0, 0, "EEM Error!", FONT_MED);
        display_text(0, 16, "Check sample", FONT_SMALL);
        display_flush();
        HAL_Delay(2000);
        g_state = STATE_IDLE;
        return;
    }

    g_eem.duration_ms = HAL_GetTick() - start;

    /* Process EEM */
    g_state = STATE_PROCESS;
}

static void run_process(void)
{
    display_clear();
    display_text(0, 0, "Processing...", FONT_MED);
    display_text(0, 14, "Mask scatter", FONT_SMALL);
    display_flush();

    eem_process(&g_eem);

    display_text(0, 24, "Features...", FONT_SMALL);
    display_flush();

    eem_extract_features(&g_eem);

    display_text(0, 34, "Classifying...", FONT_SMALL);
    display_flush();

    if (g_params.classify) {
        library_classify(&g_eem, &g_result);
    }

    /* Log to SD */
    if (g_params.log_to_sd && storage_ready()) {
        display_text(0, 44, "Saving SD...", FONT_SMALL);
        display_flush();
        storage_log_eem(&g_eem, g_params.classify ? &g_result : NULL);
        storage_log_eem_binary(&g_eem);
    }

    /* Stream over BLE */
    if (g_params.stream_ble && ble_bridge_connected()) {
        display_text(0, 54, "Streaming...", FONT_SMALL);
        display_flush();
        ble_bridge_send_eem(&g_eem);
        if (g_params.classify) {
            ble_bridge_send_result(&g_result);
        }
    }

    g_state = STATE_DISPLAY_RESULT;
}

static void run_display_result(void)
{
    static uint32_t last_update = 0;
    uint32_t now = HAL_GetTick();
    if (now - last_update < 500) return;
    last_update = now;

    display_clear();
    display_text(0, 0, "== RESULT ==", FONT_MED);

    if (g_params.classify && g_result.top_confidence > 0) {
        const library_entry_t *entry = library_get(g_result.top_match);
        if (entry) {
            display_printf(0, 12, "Match: %s", entry->name);
            display_printf(0, 22, "Conf: %.0f%%", g_result.top_confidence * 100.0f);
            display_printf(0, 32, "Ex/Em: %d/%d", entry->ex_peak_nm, entry->em_peak_nm);
            if (g_result.estimated_conc > 0) {
                display_printf(0, 42, "Conc: %.1f ug/L", g_result.estimated_conc);
            }
        }
    } else {
        display_text(0, 12, "No match found", FONT_SMALL);
        display_printf(0, 22, "Vol: %.0f", eem_volume(&g_eem));
        float ex_m, em_m;
        eem_centroid(&g_eem, &ex_m, &em_m);
        display_printf(0, 32, "Centroid: %.0f/%.0f", ex_m, em_m);
    }

    display_text(0, 50, "BTN=Home", FONT_SMALL);
    display_text(0, 56, "EEM heatmap:", FONT_SMALL);
    display_eem_heatmap(g_eem.matrix);
    display_flush();
}

static void run_log_stream(void)
{
    /* Transfer logged files via BLE */
    g_state = STATE_IDLE;
}

static void run_calibrate(void)
{
    display_clear();
    display_text(0, 0, "Calibration", FONT_MED);
    display_text(0, 14, "Place quinine", FONT_SMALL);
    display_text(0, 24, "1 ug/mL in 0.1M", FONT_SMALL);
    display_text(0, 34, "H2SO4 cuvette", FONT_SMALL);
    display_text(0, 46, "BTN=start", FONT_SMALL);
    display_flush();

    /* Actual calibration sequence would go here */
    HAL_Delay(2000);
    g_state = STATE_IDLE;
}

/* ── BLE Command Handler ──────────────────────────────── */
static void handle_ble_commands(void)
{
    uint8_t cmd;
    uint8_t payload[256];
    uint16_t len;

    while (ble_bridge_poll(&cmd, payload, &len) > 0) {
        switch (cmd) {
        case CMD_START_SCAN:
            g_state = STATE_EEM_SCAN;
            break;
        case CMD_SET_PARAMS:
            if (len >= sizeof(acq_params_t)) {
                memcpy(&g_params, payload, sizeof(acq_params_t));
            }
            break;
        case CMD_GET_STATUS:
            ble_bridge_send_status((uint8_t)g_state, power_battery_pct(), 25.0f);
            break;
        case CMD_CALIBRATE:
            g_state = STATE_CALIBRATE;
            break;
        case CMD_SET_TIME: {
            uint32_t new_time = *(uint32_t *)payload;
            /* Set RTC */
            (void)new_time;
            break;
        }
        default:
            break;
        }
    }
}

/* ── Helpers ──────────────────────────────────────────── */
static void set_status_led(uint8_t r, uint8_t g, uint8_t b)
{
    HAL_GPIO_WritePin(LED_R_GPIO, LED_R_PIN, r ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_G_GPIO, LED_G_PIN, g ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_B_GPIO, LED_B_PIN, b ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void default_params(void)
{
    memset(&g_params, 0, sizeof(g_params));
    g_params.integration_ms = CCD_INT_DEFAULT_MS;
    g_params.hdr_mode = 1;
    g_params.scan_mask = 0xFF;       /* all 8 wavelengths */
    g_params.auto_expose = 1;
    g_params.target_counts = 3000;
    g_params.led_current_ma = 50.0f;
    g_params.classify = 1;
    g_params.log_to_sd = 1;
    g_params.stream_ble = 1;
}

/* ── Button EXTI Interrupt ────────────────────────────── */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == BUTTON_PIN) {
        button_flag = 1;
    }
}

/* ── Error Handler ────────────────────────────────────── */
void Error_Handler(void)
{
    set_status_led(1, 0, 0);
    while (1) {
        HAL_Delay(500);
        HAL_GPIO_TogglePin(LED_R_GPIO, LED_R_PIN);
    }
}

/* ── Clock Config (170 MHz from HSI + PLL) ────────────── */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Configure main PLL: HSI16 → 170 MHz */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI |
                                       RCC_OSCILLATORTYPE_LSE;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.LSEState = RCC_LSE_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 4;
    RCC_OscInitStruct.PLL.PLLN = 42;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    /* CPU, AHB, APB */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK |
                                   RCC_CLOCKTYPE_SYSCLK |
                                   RCC_CLOCKTYPE_PCLK1 |
                                   RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_8) != HAL_OK) {
        Error_Handler();
    }

    /* Enable VREFINT */
    HAL_SYSCFG_EnableVREFINT();
}

/* ── Peripheral Init stubs ────────────────────────────── */
void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Button: input with falling-edge EXTI */
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = BUTTON_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(BUTTON_GPIO, &GPIO_InitStruct);

    /* Status LEDs: output push-pull */
    GPIO_InitStruct.Pin = LED_R_PIN | LED_G_PIN | LED_B_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* LED driver enable, motor enable, safety */
    GPIO_InitStruct.Pin = LED_DRV_EN_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(LED_DRV_EN_GPIO, &GPIO_InitStruct);

    /* Stepper pins */
    GPIO_InitStruct.Pin = STEPPER_IN1_PIN | STEPPER_IN2_PIN |
                         STEPPER_IN3_PIN | STEPPER_IN4_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* Stepper home: input pullup */
    GPIO_InitStruct.Pin = STEPPER_HOME_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(STEPPER_HOME_GPIO, &GPIO_InitStruct);

    /* LED select pins */
    GPIO_InitStruct.Pin = LED_SEL0_PIN | LED_SEL1_PIN | LED_SEL2_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* CCD control pins */
    GPIO_InitStruct.Pin = CCD_SI_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(CCD_SI_GPIO, &GPIO_InitStruct);

    /* One-wire: open-drain */
    GPIO_InitStruct.Pin = ONEWIRE_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_GPIO, &GPIO_InitStruct);

    /* CS pins */
    GPIO_InitStruct.Pin = SD_CS_PIN | OLED_CS_PIN | OLED_DC_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    HAL_GPIO_WritePin(SD_CS_GPIO, SD_CS_PIN, GPIO_PIN_SET);

    /* EXTI interrupt for button */
    HAL_NVIC_SetPriority(EXTI_15_10_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI_15_10_IRQn);
}

void MX_ADC1_Init(void)
{
    __HAL_RCC_ADC12_CLK_ENABLE();

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV8;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = ENABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    if (HAL_ADC_Init(&hadc1) != HAL_OK) Error_Handler();

    /* Configure channels */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_2;  /* PA1 - REF_PD */
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}

void MX_ADC2_Init(void)
{
    hadc2.Instance = ADC2;
    hadc2.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV8;
    hadc2.Init.Resolution = ADC_RESOLUTION_12B;
    hadc2.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc2.Init.ScanMode = ADC_SCAN_DISABLE;
    hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc2.Init.ContinuousConvMode = DISABLE;
    hadc2.Init.NbrOfConversion = 1;
    hadc2.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    if (HAL_ADC_Init(&hadc2) != HAL_OK) Error_Handler();

    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_4;  /* PA3 - CCD_AO */
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc2, &sConfig);
}

void MX_I2C1_Init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();

    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x30A0A130;  /* 400 kHz @ 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK) Error_Handler();

    HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE);
}

void MX_SPI1_Init(void)
{
    __HAL_RCC_SPI1_CLK_ENABLE();

    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_HIGH;
    hspi1.Init.CLKPhase = SPI_PHASE_2EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;  /* ~21 MHz */
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    if (HAL_SPI_Init(&hspi1) != HAL_OK) Error_Handler();
}

void MX_TIM2_Init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();

    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 0;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 8499;  /* 170MHz / (8500) = 20 kHz → 10-bit PWM at ~9.8 kHz */
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_PWM_Init(&htim2);

    TIM_OC_InitTypeDef sConfig = {0};
    sConfig.OCMode = TIM_OCMODE_PWM1;
    sConfig.Pulse = 0;
    sConfig.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfig.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim2, &sConfig, TIM_CHANNEL_1);
}

void MX_TIM3_Init(void)
{
    __HAL_RCC_TIM3_CLK_ENABLE();

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 0;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    /* 170 MHz → 2 MHz: period = 85-1 */
    htim3.Init.Period = 84;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_Base_Init(&htim3);

    TIM_OC_InitTypeDef sConfig = {0};
    sConfig.OCMode = TIM_OCMODE_TOGGLE;
    sConfig.Pulse = 42;
    sConfig.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim3, &sConfig, TIM_CHANNEL_1);
}

void MX_USART3_UART_Init(void)
{
    __HAL_RCC_USART3_CLK_ENABLE();

    huart3.Instance = USART3;
    huart3.Init.BaudRate = UART_BAUD;
    huart3.Init.WordLength = UART_WORDLENGTH_8B;
    huart3.Init.StopBits = UART_STOPBITS_1;
    huart3.Init.Parity = UART_PARITY_NONE;
    huart3.Init.Mode = UART_MODE_TX_RX;
    huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart3.Init.OverSampling = UART_OVERSAMPLING_16;
    huart3.Init.OneBitSampling = UART_ONEBIT_SAMPLING_DISABLE;
    huart3.Init.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart3) != HAL_OK) Error_Handler();
}