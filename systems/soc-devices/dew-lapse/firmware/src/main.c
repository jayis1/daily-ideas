/* main.c — Frost Point firmware entry point.
 *
 * Initializes all peripherals (HAL boilerplate condensed), starts the
 * sensor tasks, and runs the cooperative super-loop: 1 kHz sampler ISR,
 * 10 Hz controller, 1 Hz application.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "tec.h"
#include "adc_ads122.h"
#include "optics.h"
#include "sensors.h"
#include "oled.h"
#include "ble.h"
#include "flash_log.h"
#include "state_machine.h"
#include "dewpoint.h"
#include <stdio.h>

TIM_HandleTypeDef htim2;   /* TEC PWM */
TIM_HandleTypeDef htim3;   /* IR chopper */
ADC_HandleTypeDef hadc1;  /* STM32 ADC */
I2C_HandleTypeDef hi2c1;  /* ADS122U04 */
I2C_HandleTypeDef hi2c3;  /* sensors + OLED */
SPI_HandleTypeDef hspi1;  /* W25Q128 */
UART_HandleTypeDef hlpuart1; /* BLE */
UART_HandleTypeDef huart3;  /* debug */

volatile uint16_t adc_raw[2];  /* TEC V/I */

static uint32_t last_controller_ms = 0;
static uint32_t last_application_ms = 0;

uint32_t hal_millis(void) { return HAL_GetTick(); }

/* ---- HAL boilerplate (condensed) ----------------------------------- */
void SystemClock_Config(void)
{
    /* Configure 80 MHz from 8 MHz HSE + 32.768 kHz LSE for RTC.
     * (Standard STM32CubeMX output — abbreviated here.) */
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_LSE;
    o.HSEState = RCC_HSE_ON;
    o.LSEState = RCC_LSE_ON;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = 1;
    o.PLL.PLLN = 20;
    o.PLL.PLLP = RCC_PLLP_DIV7;
    o.PLL.PLLQ = RCC_PLLQ_DIV2;
    o.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&o);
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV1;
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&c, FLASH_LATENCY_4);
}

static void gpio_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    /* PA2: TIM2_CH1 PWM, PA3: GPIO out, PA5/PA6/PA7: GPIO out */
    g.Pin = GPIO_PIN_2;
    g.Mode = GPIO_MODE_AF_PP;
    g.Alternate = GPIO_AF1_TIM2;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &g);
    g.Pin = GPIO_PIN_3 | GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Alternate = 0;
    HAL_GPIO_Init(GPIOA, &g);
    /* PB1: TIM3_CH4 chop, PB5/6/7/12/13: GPIO/SPI */
    g.Pin = GPIO_PIN_1;
    g.Mode = GPIO_MODE_AF_PP;
    g.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOB, &g);
    /* PC13: user button input */
    g.Pin = GPIO_PIN_13;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &g);
}

static void tim2_init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = (APB1_FREQ / TEC_PWM_HZ) / TEC_PWM_MAX - 1;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = TEC_PWM_MAX - 1;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim2);
    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_1);
}

static void tim3_init(void)
{
    __HAL_RCC_TIM3_CLK_ENABLE();
    htim3.Instance = TIM3;
    htim3.Init.Prescaler = (APB1_FREQ / IR_CHOP_HZ) - 1;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 1;  /* toggle at 38 kHz */
    HAL_TIM_PWM_Init(&htim3);
    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 1;
    HAL_TIM_PWM_ConfigChannel(&htim3, &oc, TIM_CHANNEL_4);
}

static void i2c_init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();
    __HAL_RCC_I2C3_CLK_ENABLE();
    /* GPIO AF4 for I2C1 (PB8/PB9) and I2C3 (PA8/PA9) */
    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_AF_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    g.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &g);
    g.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    g.Alternate = GPIO_AF4_I2C3;
    HAL_GPIO_Init(GPIOA, &g);
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10909CEC;  /* 100 kHz for L4 @ 80 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
    hi2c3.Instance = I2C3;
    hi2c3.Init = hi2c1.Init;
    HAL_I2C_Init(&hi2c3);
}

static void spi_init(void)
{
    __HAL_RCC_SPI1_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Alternate = GPIO_AF5_SPI1;
    g.Pin = GPIO_PIN_3 | GPIO_PIN_4 | GPIO_PIN_5;
    HAL_GPIO_Init(GPIOB, &g);
    g.Pin = GPIO_PIN_6;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOB, &g);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_HIGH;
    hspi1.Init.CLKPhase = SPI_PHASE_2EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi1);
}

static void adc_init(void)
{
    __HAL_RCC_ADC_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_ANALOG_ADC_CONTROL;
    g.Pin = GPIO_PIN_0 | GPIO_PIN_1;
    HAL_GPIO_Init(GPIOA, &g);
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV8;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ADC_SCAN_ENABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 2;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    HAL_ADC_Init(&hadc1);
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_5; ch.Rank = 1; ch.SamplingTime = ADC_SAMPLETIME_24CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &ch);
    ch.Channel = ADC_CHANNEL_6; ch.Rank = 2;
    HAL_ADC_ConfigChannel(&hadc1, &ch);
}

static void uart_init(void)
{
    __HAL_RCC_LPUART1_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Alternate = GPIO_AF8_LPUART1;
    g.Pin = GPIO_PIN_10 | GPIO_PIN_11;
    HAL_GPIO_Init(GPIOA, &g);
    hlpuart1.Instance = LPUART1;
    hlpuart1.Init.BaudRate = BLE_UART_BAUD;
    hlpuart1.Init.WordLength = UART_WORDLENGTH_8B;
    hlpuart1.Init.StopBits = UART_STOPBITS_1;
    hlpuart1.Init.Parity = UART_PARITY_NONE;
    hlpuart1.Init.Mode = UART_MODE_TX_RX;
    HAL_UART_Init(&hlpuart1);
}

/* ---- Super-loop main ----------------------------------------------- */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    gpio_init();
    tim2_init();
    tim3_init();
    i2c_init();
    spi_init();
    adc_init();
    uart_init();

    /* Peripherals */
    tec_init();
    ads122_init();
    optics_init();
    oled_init();
    ble_init();
    log_start();

    /* Sensors */
    bme280_init();
    scd41_init();
    sht45_read(NULL, NULL);  /* prime */

    sm_init();

    /* Enable IWDG watchdog */
    HAL_IWDG_Refresh(&hiwdg);

    uint32_t now;
    while (1) {
        now = HAL_GetTick();

        /* 10 Hz controller */
        if (now - last_controller_ms >= 100) {
            float dt = (now - last_controller_ms) / 1000.0f;
            last_controller_ms = now;
            sm_controller_tick(dt);
        }

        /* 1 Hz application */
        if (now - last_application_ms >= 1000) {
            last_application_ms = now;
            sm_application_tick();
        }

        /* User button: start measurement */
        if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET) {
            HAL_Delay(20);  /* debounce */
            if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET) {
                sm_start_measurement();
            }
        }

        HAL_IWDG_Refresh(&hiwdg);
    }
}

/* Fault handler */
void HardFault_Handler(void)
{
    while (1) { __NOP(); }
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}