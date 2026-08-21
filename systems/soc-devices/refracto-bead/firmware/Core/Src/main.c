/**
 * main.c — Refracto Bead Pocket Digital Abbe Refractometer
 *
 * Entry point: initializes all peripherals, loads calibration from flash,
 * registers button handlers, and runs the main measurement state machine.
 *
 * MCU: STM32G491RET6 (170 MHz Cortex-M4F, CORDIC, 12-bit ADC)
 */

#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tsl1402r.h"
#include "edge_detect.h"
#include "refract_calc.h"
#include "compound_lib.h"
#include "ds18b20.h"
#include "bme280.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "esp32_link.h"
#include "power_manager.h"

/* ---- GPIO pin definitions (match schematic) ---- */
#define LED1_EN_PIN     GPIO_PIN_3   /* PA3 — 589 nm */
#define LED2_EN_PIN     GPIO_PIN_4   /* PA4 — 525 nm */
#define LED3_EN_PIN     GPIO_PIN_5   /* PA5 — 470 nm */
#define LED4_EN_PIN     GPIO_PIN_6   /* PA6 — 655 nm */
#define LED_PORT        GPIOA

#define BTN_MEASURE_PIN GPIO_PIN_8   /* PB8 */
#define BTN_MODE_PIN    GPIO_PIN_9   /* PB9 */
#define BTN_POWER_PIN   GPIO_PIN_10  /* PB10 */
#define BTN_PORT        GPIOB

#define ESP_EN_PIN      GPIO_PIN_2   /* PB2 */
#define STAT_LED_PIN    GPIO_PIN_7   /* PB7 */

/* ---- Measurement modes ---- */
typedef enum {
    MODE_RI = 0,
    MODE_BRIX,
    MODE_SG,
    MODE_COOL,
    MODE_ALC,
    MODE_COUNT
} measure_mode_t;

static const char *mode_names[MODE_COUNT] = {
    "RI", "BRIX", "SG", "COOL", "ALC"
};

/* ---- Shared state ---- */
static volatile measure_mode_t current_mode = MODE_RI;
static volatile uint8_t measure_pending = 0;
static volatile uint8_t mode_changed = 0;

/* CCD capture buffer (256 pixels, 16-bit ADC values) */
static uint16_t ccd_buffer[TSL1402R_NUM_PIXELS];

/* Dark offset (measured at boot with LEDs off) */
static uint16_t ccd_dark_offset[TSL1402R_NUM_PIXELS];

/* ---- Interrupt handlers ---- */
void HAL_GPIO_EXTI_Callback(uint16_t pin) {
    if (pin == BTN_MEASURE_PIN) {
        measure_pending = 1;
    } else if (pin == BTN_MODE_PIN) {
        mode_changed = 1;
    } else if (pin == BTN_POWER_PIN) {
        /* Handled in main loop with debounce */
    }
}

/* ---- System Clock Configuration ---- */
void SystemClock_Config(void) {
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 1;
    osc.PLL.PLLN = 42;       /* 8 MHz / 1 * 42 / 2 = 168 MHz ≈ 170 MHz */
    osc.PLL.PLLP = RCC_PLLP_DIV7;
    osc.PLL.PLLQ = RCC_PLLQ_DIV2;
    osc.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);
}

/* ---- GPIO Init ---- */
void MX_GPIO_Init(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();

    GPIO_InitTypeDef gp = {0};

    /* LED enable pins (output) */
    gp.Pin = LED1_EN_PIN | LED2_EN_PIN | LED3_EN_PIN | LED4_EN_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_PORT, &gp);
    HAL_GPIO_WritePin(LED_PORT, LED1_EN_PIN | LED2_EN_PIN |
                              LED3_EN_PIN | LED4_EN_PIN, GPIO_PIN_RESET);

    /* ESP_EN (output) */
    gp.Pin = ESP_EN_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOB, &gp);
    HAL_GPIO_WritePin(GPIOB, ESP_EN_PIN, GPIO_PIN_SET); /* Enable ESP32-C3 */

    /* STAT_LED (output) */
    gp.Pin = STAT_LED_PIN;
    HAL_GPIO_Init(GPIOB, &gp);
    HAL_GPIO_WritePin(GPIOB, STAT_LED_PIN, GPIO_PIN_RESET);

    /* Button pins (input with EXTI, falling edge) */
    gp.Pin = BTN_MEASURE_PIN | BTN_MODE_PIN | BTN_POWER_PIN;
    gp.Mode = GPIO_MODE_IT_FALLING;
    gp.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(BTN_PORT, &gp);

    /* EXTI interrupts */
    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
    HAL_NVIC_SetPriority(EXTI10_15_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI10_15_IRQn);
}

/* ---- ADC Init (for CCD AO + battery sense) ---- */
ADC_HandleTypeDef hadc1;

void MX_ADC1_Init(void) {
    __HAL_RCC_ADC12_CLK_ENABLE();

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    HAL_ADC_Init(&hadc1);

    /* Calibration */
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
}

/* ---- TIM2 Init (CCD clock + SI pulse generation) ---- */
TIM_HandleTypeDef htim2;

void MX_TIM2_Init(void) {
    __HAL_RCC_TIM2_CLK_ENABLE();

    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 0;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 84;  /* 168MHz / 2 / 84 = 1 MHz CCD clock */
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV2;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_PWM_Init(&htim2);

    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 42;            /* 50% duty */
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_1);  /* TSL_CLK on PA1 */

    /* Channel 2 for SI pulse (one-shot) */
    oc.Pulse = 0;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_2);  /* TSL_SI on PA2 */

    TIM_MasterConfigTypeDef mc = {0};
    mc.MasterOutputTrigger = TIM_TRGO_RESET;
    HAL_TIMEx_MasterConfigSynchronization(&htim2, &mc);
}

/* ---- I2C1 Init (OLED + BME280) ---- */
I2C_HandleTypeDef hi2c1;

void MX_I2C1_Init(void) {
    __HAL_RCC_I2C1_CLK_ENABLE();

    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x30A0A7FB;  /* 400 kHz @ 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

/* ---- SPI2 Init (microSD) ---- */
SPI_HandleTypeDef hspi2;

void MX_SPI2_Init(void) {
    __HAL_RCC_SPI2_CLK_ENABLE();

    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8; /* 170/8 ≈ 21 MHz */
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi2.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi2.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    HAL_SPI_Init(&hspi2);
}

/* ---- USART1 Init (to ESP32-C3 @ 460800) ---- */
UART_HandleTypeDef huart1;

void MX_USART1_Init(void) {
    __HAL_RCC_USART1_CLK_ENABLE();

    huart1.Instance = USART1;
    huart1.Init.BaudRate = 460800;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart1);
}

/* ---- LED control ---- */
typedef enum {
    LED_589 = 0,
    LED_525,
    LED_470,
    LED_655
} led_wavelength_t;

static const uint16_t led_pins[4] = {
    LED1_EN_PIN, LED2_EN_PIN, LED3_EN_PIN, LED4_EN_PIN
};

static void led_on(led_wavelength_t wl) {
    HAL_GPIO_WritePin(LED_PORT, led_pins[wl], GPIO_PIN_SET);
}

static void led_off(led_wavelength_t wl) {
    HAL_GPIO_WritePin(LED_PORT, led_pins[wl], GPIO_PIN_RESET);
}

static void all_leds_off(void) {
    HAL_GPIO_WritePin(LED_PORT, LED1_EN_PIN | LED2_EN_PIN |
                              LED3_EN_PIN | LED4_EN_PIN, GPIO_PIN_RESET);
}

/* ---- Measure dark offset ---- */
static void measure_dark_offset(void) {
    all_leds_off();
    HAL_Delay(50);
    tsl1402r_read(ccd_dark_offset);
    /* Subtract a baseline (ambient light with LEDs off) */
    for (int i = 0; i < TSL1402R_NUM_PIXELS; i++) {
        if (ccd_dark_offset[i] < 10) ccd_dark_offset[i] = 0;
    }
}

/* ---- Run a complete measurement cycle ---- */
static void run_measurement(void) {
    /* Read temperatures */
    float t_prism = ds18b20_read_temperature();
    float t_amb = 0, hum = 0, pres = 0;
    bme280_read(&t_amb, &hum, &pres);

    oled_display_measuring(0);

    /* Result structure */
    ri_result_t result;
    memset(&result, 0, sizeof(result));
    result.t_prism = t_prism;
    result.t_ambient = t_amb;

    /* 4-wavelength sweep */
    static const led_wavelength_t leds[4] = {LED_589, LED_525, LED_470, LED_655};
    static const float wavelengths[4] = {589.0f, 525.0f, 470.0f, 655.0f};
    float n_values[4];

    for (int i = 0; i < 4; i++) {
        led_on(leds[i]);
        HAL_Delay(20);  /* Let illumination stabilize */

        /* Read CCD (auto-exposure handled inside tsl1402r_read) */
        tsl1402r_read(ccd_buffer);

        led_off(leds[i]);

        /* Subtract dark offset */
        for (int p = 0; p < TSL1402R_NUM_PIXELS; p++) {
            if (ccd_buffer[p] > ccd_dark_offset[p])
                ccd_buffer[p] -= ccd_dark_offset[p];
            else
                ccd_buffer[p] = 0;
        }

        /* Find the bright/dark boundary */
        float p_edge = edge_detect_find_boundary(ccd_buffer, TSL1402R_NUM_PIXELS);

        /* Convert pixel position to refractive index */
        n_values[i] = refract_calc_ri(p_edge, wavelengths[i], t_prism);

        /* Update progress */
        oled_display_measuring((uint8_t)((i + 1) * 25));

        /* Small delay between wavelengths */
        HAL_Delay(10);
    }

    all_leds_off();

    /* Compute derived quantities (n_D, dispersion, Abbe V_D, Brix, SG, ABV) */
    refract_calc_derive(n_values, wavelengths, t_prism, &result);

    /* Match against compound library (k-NN) */
    compound_lib_match(&result);

    /* Display results on OLED */
    oled_display_results(current_mode, &result);

    /* Log to SD card */
    sd_logger_write(&result);

    /* Send to ESP32-C3 for BLE/Wi-Fi relay */
    esp32_link_send_result(&result);

    /* Blink status LED */
    HAL_GPIO_WritePin(GPIOB, STAT_LED_PIN, GPIO_PIN_SET);
    HAL_Delay(100);
    HAL_GPIO_WritePin(GPIOB, STAT_LED_PIN, GPIO_PIN_RESET);
}

/* ---- Button task (debounced) ---- */
static void handle_buttons(void) {
    static uint32_t last_mode_press = 0;
    static uint32_t last_measure_press = 0;
    static uint32_t measure_press_start = 0;
    uint32_t now = HAL_GetTick();

    /* Mode button */
    if (mode_changed && (now - last_mode_press > 200)) {
        mode_changed = 0;
        last_mode_press = now;
        if (HAL_GPIO_ReadPin(BTN_PORT, BTN_MODE_PIN) == GPIO_PIN_RESET) {
            current_mode = (current_mode + 1) % MODE_COUNT;
            oled_display_mode_select(current_mode, mode_names[current_mode]);
        }
    }

    /* Measure button (with long-press detection for calibration) */
    if (measure_pending && (now - last_measure_press > 200)) {
        measure_pending = 0;
        last_measure_press = now;
        if (HAL_GPIO_ReadPin(BTN_PORT, BTN_MEASURE_PIN) == GPIO_PIN_RESET) {
            measure_press_start = now;
            /* Wait for release */
            while (HAL_GPIO_ReadPin(BTN_PORT, BTN_MEASURE_PIN) == GPIO_PIN_RESET) {
                HAL_Delay(10);
            }
            uint32_t hold_time = HAL_GetTick() - measure_press_start;

            if (hold_time > 3000) {
                /* Long press: enter calibration mode */
                oled_display_calibration_prompt();
                HAL_Delay(2000);  /* Simplified — real impl waits for user */
                /* TODO: trigger 2-point calibration sequence */
            } else {
                /* Short press: start measurement */
                run_measurement();
            }
        }
    }

    /* Power button: enter Stop mode */
    if (HAL_GPIO_ReadPin(BTN_PORT, BTN_POWER_PIN) == GPIO_PIN_RESET) {
        HAL_Delay(50);  /* Debounce */
        if (HAL_GPIO_ReadPin(BTN_PORT, BTN_POWER_PIN) == GPIO_PIN_RESET) {
            oled_display_off();
            all_leds_off();
            HAL_GPIO_WritePin(GPIOB, ESP_EN_PIN, GPIO_PIN_RESET); /* Power down ESP32 */
            power_manager_enter_stop();
            /* Wakes here on button press — re-init clocks */
            SystemClock_Config();
            HAL_GPIO_WritePin(GPIOB, ESP_EN_PIN, GPIO_PIN_SET);
            oled_display_init();
        }
    }
}

/* ---- Main ---- */
int main(void) {
    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_TIM2_Init();
    MX_I2C1_Init();
    MX_SPI2_Init();
    MX_USART1_Init();

    /* Initialize peripherals */
    oled_display_init();
    bme280_init();
    ds18b20_init();
    tsl1402r_init(&htim2, &hadc1);
    sd_logger_init(&hspi2);
    esp32_link_init(&huart1);
    compound_lib_init();
    refract_calc_init();

    /* Measure dark offset for CCD */
    measure_dark_offset();

    /* Boot screen */
    oled_display_boot_screen();
    HAL_Delay(1000);
    oled_display_idle_screen(100, 20.0f, 45.0f, mode_names[current_mode]);

    /* Main loop */
    while (1) {
        handle_buttons();

        /* Update idle display periodically */
        static uint32_t last_idle_update = 0;
        uint32_t now = HAL_GetTick();
        if (now - last_idle_update > 1000) {
            last_idle_update = now;
            float t_amb, hum, pres;
            bme280_read(&t_amb, &hum, &pres);
            uint8_t batt = power_manager_read_battery();
            oled_display_idle_screen(batt, t_amb, hum, mode_names[current_mode]);
        }

        /* Enter low-power wait for interrupt */
        __WFI();
    }
}

/* ---- EXTI interrupt handlers ---- */
void EXTI9_5_IRQHandler(void) {
    HAL_GPIO_EXTI_IRQHandler(BTN_MEASURE_PIN);
    HAL_GPIO_EXTI_IRQHandler(BTN_MODE_PIN);
}

void EXTI10_15_IRQHandler(void) {
    HAL_GPIO_EXTI_IRQHandler(BTN_POWER_PIN);
}

/* ---- Error handler ---- */
void Error_Handler(void) {
    HAL_GPIO_WritePin(GPIOB, STAT_LED_PIN, GPIO_PIN_SET);
    while (1) {
        HAL_Delay(500);
        HAL_GPIO_TogglePin(GPIOB, STAT_LED_PIN);
    }
}