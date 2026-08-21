/*
 * main.c — Opti Rot entry point
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Initializes STM32G491 HAL, CORDIC, DACs (LED intensity), ADC (photodiode),
 * I2C (OLED + DS18B20), SPI (SD card), UART (ESP32-C3 bridge), stepper motor,
 * and launches the main measurement loop driven by the UI state machine.
 *
 * Core loop:
 *   1. Poll buttons (debounced)
 *   2. Run current mode's task (Measure/Identify/Monitor/etc.)
 *   3. Update OLED display
 *   4. Handle UART commands from ESP32-C3 (BLE/Wi-Fi relay)
 *   5. Log to SD card if applicable
 *   6. Sleep if idle timeout reached
 */
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

#include "sdkconfig.h"
#include "stepper.h"
#include "photodiode.h"
#include "polarimeter.h"
#include "drude.h"
#include "temperature.h"
#include "library.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "ui.h"
#include "led.h"

/* Global handles — set in HAL_MspInit / main() */
ADC_HandleTypeDef hadc1;
DAC_HandleTypeDef hdac1;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi2;
UART_HandleTypeDef huart2;
CORDIC_HandleTypeDef hcordic;
TIM_HandleTypeDef htim2;

static uint8_t current_mode = UI_MODE_MEASURE;
static uint32_t last_activity_ms = 0;
static uint8_t sleep_active = 0;

/* ---- Clock / peripheral init ---- */

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* PLL from HSI (16 MHz) → 170 MHz */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 4;
    RCC_OscInitStruct.PLL.PLLN = 42;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                 | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);
}

static void CORDIC_Init(void)
{
    hcordic.Instance = CORDIC;
    HAL_CORDIC_DeInit(&hcordic);
    hcordic.Init.Function = CORDIC_FUNCTION_COSINE;
    hcordic.Init.Precision = CORDIC_PRECISION_6CYCLES;
    hcordic.Init.Scale = CORDIC_SCALE_0;
    HAL_CORDIC_Init(&hcordic);
}

static void ADC1_Init(void)
{
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNAL_TRIG_CONV_EDGE_NONE;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.OversamplingMode = DISABLE;
    HAL_ADC_Init(&hadc1);
}

static void DAC1_Init(void)
{
    DAC_ChannelConfTypeDef sConfig = {0};
    hdac1.Instance = DAC1;
    HAL_DAC_Init(&hdac1);
    sConfig.DAC_SampleAndHold = DAC_SAMPLEANDHOLD_DISABLE;
    sConfig.DAC_Trigger = DAC_TRIGGER_NONE;
    sConfig.DAC_OutputBuffer = DAC_OUTPUTBUFFER_ENABLE;
    HAL_DAC_ConfigChannel(&hdac1, &sConfig, DAC_CHANNEL_1);
    HAL_DAC_ConfigChannel(&hdac1, &sConfig, DAC_CHANNEL_2);
}

static void I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10909CEC;  /* 400 kHz @ 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void SPI2_Init(void)
{
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;  /* 21 MHz */
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi2);
}

static void UART2_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = BLE_UART_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart2);
}

/* ---- Main ---- */

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* Enable all needed GPIO clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_ADC1_CLK_ENABLE();
    __HAL_RCC_DAC1_CLK_ENABLE();
    __HAL_RCC_I2C1_CLK_ENABLE();
    __HAL_RCC_SPI2_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_CORDIC_CLK_ENABLE();

    CORDIC_Init();
    ADC1_Init();
    DAC1_Init();
    I2C1_Init();
    SPI2_Init();
    UART2_Init();

    /* Subsystem init */
    led_init();
    display_init();
    display_splash("OPTI ROT", "v1.0");
    HAL_Delay(1500);

    temperature_init();
    stepper_init();
    photodiode_init();
    polarimeter_init();
    library_init();
    sd_log_init();
    ble_bridge_init();
    ui_init();

    /* Set default LED intensity (589nm) */
    polarimeter_set_wavelength(WAVELENGTH_589_NM);

    /* Load custom library entries from SD if present */
    library_load_from_sd();

    led_set_color(LED_COLOR_GREEN, 50);
    display_main_menu(current_mode);

    uint32_t last_temp_ms = 0;
    double current_temp = 20.0;

    while (1) {
        uint32_t now = HAL_GetTick();

        /* Poll buttons */
        uint8_t button = ui_poll_buttons();
        if (button != UI_BUTTON_NONE) {
            last_activity_ms = now;
            sleep_active = 0;
            if (button == UI_BUTTON_MODE) {
                current_mode = (current_mode + 1) % UI_MODE_COUNT;
                display_main_menu(current_mode);
            } else if (button == UI_BUTTON_MEAS) {
                ui_execute_mode(current_mode);
            } else if (button == UI_BUTTON_CAL) {
                polarimeter_auto_zero();
                display_message("Zeroed", NULL);
                HAL_Delay(800);
                display_main_menu(current_mode);
            }
        }

        /* Periodic temperature read (every 5 seconds) */
        if (now - last_temp_ms > 5000) {
            current_temp = temperature_read();
            last_temp_ms = now;
            display_update_temperature(current_temp);
        }

        /* Handle UART commands from ESP32-C3 */
        ble_bridge_poll();

        /* Sleep timeout */
        if (!sleep_active && (now - last_activity_ms > SLEEP_TIMEOUT_S * 1000)) {
            sleep_active = 1;
            stepper_deenergize();
            display_off();
            led_set_color(LED_COLOR_OFF, 0);
        }

        HAL_Delay(10);  /* 100 Hz main loop */
    }
}

/* ---- Interrupt handlers ---- */

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void HardFault_Handler(void)
{
    while (1) {
        led_set_color(LED_COLOR_RED, 200);
        HAL_Delay(200);
        led_set_color(LED_COLOR_OFF, 0);
        HAL_Delay(200);
    }
}