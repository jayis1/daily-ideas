/*
 * main.c — Main firmware for Phyto Pulse
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * STM32G474RET6: continuous 1 kHz plant electrophysiology acquisition,
 * spike detection + int8 CNN classification, SD logging, OLED display,
 * BLE/Wi-Fi streaming via ESP32-C3.
 */

#include "main.h"
#include "ads1256.h"
#include "ina333.h"
#include "spike_detect.h"
#include "spike_classify.h"
#include "slow_wave.h"
#include "experiment.h"
#include "sd_logger.h"
#include "esp32_link.h"
#include "oled_display.h"
#include "bme280.h"
#include "power_manager.h"
#include <string.h>
#include <stdio.h>

/* ---- HAL handles (from STM32CubeMX) ---- */
ADC_HandleTypeDef hadc1;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1;
SPI_HandleTypeDef hspi2;
UART_HandleTypeDef huart1;
RTC_HandleTypeDef hrtc;

/* GPIO pin aliases (from CubeMX main.h) */
#define ADC_CS_GPIO_Port    GPIOA
#define ADC_CS_Pin          GPIO_PIN_4
#define ADC_DRDY_GPIO_Port  GPIOA
#define ADC_DRDY_Pin        GPIO_PIN_15
#define ESP_EN_GPIO_Port    GPIOB
#define ESP_EN_Pin         GPIO_PIN_2
#define STIM_EN_GPIO_Port   GPIOB
#define STIM_EN_Pin        GPIO_PIN_14
#define SD_DETECT_GPIO_Port GPIOC
#define SD_DETECT_Pin      GPIO_PIN_14
#define CHARGE_STAT_GPIO_Port GPIOB
#define CHARGE_STAT_Pin    GPIO_PIN_15
#define GAIN_SEL0_GPIO_Port GPIOB
#define GAIN_SEL0_Pin      GPIO_PIN_11
#define GAIN_SEL1_GPIO_Port GPIOB
#define GAIN_SEL1_Pin      GPIO_PIN_12
#define GAIN_SEL2_GPIO_Port GPIOB
#define GAIN_SEL2_Pin      GPIO_PIN_13

/* ---- Application state ---- */
typedef enum {
    APP_STATE_IDLE = 0,
    APP_STATE_ARMING,
    APP_STATE_RECORDING,
    APP_STATE_STOPPING,
} app_state_t;

static app_state_t  g_app_state = APP_STATE_IDLE;
static uint32_t     g_session_start_ms;
static int32_t      g_sample_idx;
static uint16_t     g_event_count;
static uint16_t     g_ap_count, g_vp_count, g_art_count;
static float        g_peak_amplitude_window;  /* for auto-ranging */
static uint32_t     g_last_autorange_ms;
static uint32_t     g_last_display_ms;
static uint32_t     g_last_sample_send_ms;
static bool         g_button_record_pressed;

void SystemClock_Config(void)
{
    /* 170 MHz from 8 MHz HSE + PLL (from CubeMX) */
    RCC_OscInitTypeDef osc = {0};
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 1;
    osc.PLL.PLLN = 42;
    osc.PLL.PLLP = RCC_PLLP_DIV7;
    osc.PLL.PLLQ = RCC_PLLQ_DIV2;
    osc.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&osc);

    RCC_ClkInitTypeDef clk = {0};
    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_8);
}

static void gpio_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef gi = {0};

    /* ADC CS (PA4) */
    gi.Pin = ADC_CS_Pin;
    gi.Mode = GPIO_MODE_OUTPUT_PP;
    gi.Pull = GPIO_NOPULL;
    gi.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ADC_CS_GPIO_Port, &gi);
    HAL_GPIO_WritePin(ADC_CS_GPIO_Port, ADC_CS_Pin, GPIO_PIN_SET);

    /* ADC DRDY (PA15) — EXTI falling */
    gi.Pin = ADC_DRDY_Pin;
    gi.Mode = GPIO_MODE_IT_FALLING;
    gi.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ADC_DRDY_GPIO_Port, &gi);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 5);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

    /* ESP_EN (PB2) */
    gi.Pin = ESP_EN_Pin;
    gi.Mode = GPIO_MODE_OUTPUT_PP;
    gi.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(ESP_EN_GPIO_Port, &gi);
    HAL_GPIO_WritePin(ESP_EN_GPIO_Port, ESP_EN_Pin, GPIO_PIN_RESET);

    /* STIM_EN (PB14) */
    gi.Pin = STIM_EN_Pin;
    gi.Mode = GPIO_MODE_OUTPUT_PP;
    gi.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(STIM_EN_GPIO_Port, &gi);
    HAL_GPIO_WritePin(STIM_EN_GPIO_Port, STIM_EN_Pin, GPIO_PIN_RESET);

    /* Gain select (PB11, PB12, PB13) */
    gi.Pin = GPIO_PIN_11 | GPIO_PIN_12 | GPIO_PIN_13;
    gi.Mode = GPIO_MODE_OUTPUT_PP;
    gi.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOB, &gi);

    /* Buttons (PB8, PB9, PB10) — active low */
    gi.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    gi.Mode = GPIO_MODE_INPUT;
    gi.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOB, &gi);

    /* SD detect (PC14) */
    gi.Pin = SD_DETECT_Pin;
    gi.Mode = GPIO_MODE_INPUT;
    gi.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(SD_DETECT_GPIO_Port, &gi);

    /* Charge status (PB15) */
    gi.Pin = CHARGE_STAT_Pin;
    gi.Mode = GPIO_MODE_INPUT;
    gi.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(CHARGE_STAT_GPIO_Port, &gi);
}

static void spi1_init(void)
{
    __HAL_RCC_SPI1_CLK_ENABLE();
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8; /* 170/8 = 21 MHz */
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi1);

    /* DMA for SPI1 RX */
    __HAL_RCC_DMA1_CLK_ENABLE();
    DMA_HandleTypeDef hdma_spi1_rx = {0};
    hdma_spi1_rx.Instance = DMA1_Channel2;
    hdma_spi1_rx.Init.Request = DMA_REQUEST_SPI1_RX;
    hdma_spi1_rx.Init.Direction = DMA_PERIPH_TO_MEMORY;
    hdma_spi1_rx.Init.PeriphInc = DMA_PINC_DISABLE;
    hdma_spi1_rx.Init.MemInc = DMA_MINC_ENABLE;
    hdma_spi1_rx.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
    hdma_spi1_rx.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
    hdma_spi1_rx.Init.Mode = DMA_NORMAL;
    hdma_spi1_rx.Init.Priority = DMA_PRIORITY_HIGH;
    HAL_DMA_Init(&hdma_spi1_rx);
    __HAL_LINKDMA(&hspi1, hdmarx, hdma_spi1_rx);
    HAL_NVIC_SetPriority(DMA1_Channel2_IRQn, 5);
    HAL_NVIC_EnableIRQ(DMA1_Channel2_IRQn);
}

static void spi2_init(void)
{
    __HAL_RCC_SPI2_CLK_ENABLE();
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_HIGH;
    hspi2.Init.CLKPhase = SPI_PHASE_2EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4; /* 170/4 = 42 MHz */
    HAL_SPI_Init(&hspi2);
}

static void i2c1_init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10909CEC; /* 400 kHz for 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void usart1_init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 460800;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    HAL_UART_Init(&huart1);
}

static void adc1_init(void)
{
    __HAL_RCC_ADC1_CLK_ENABLE();
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    HAL_ADC_Init(&hadc1);

    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_1;
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES;
    HAL_ADC_ConfigChannel(&hadc1, &ch);
}

static void buttons_scan(void)
{
    static uint32_t last_debounce[3] = {0, 0, 0};
    static uint8_t  last_state[3] = {1, 1, 1};
    uint32_t now = HAL_GetTick();

    uint16_t pins[] = {GPIO_PIN_8, GPIO_PIN_9, GPIO_PIN_10};
    for (int i = 0; i < 3; i++) {
        uint8_t state = HAL_GPIO_ReadPin(GPIOB, pins[i]);
        if (state != last_state[i]) {
            last_debounce[i] = now;
            last_state[i] = state;
        }
        if (state == 0 && (now - last_debounce[i]) > 50) {
            /* Pressed */
            if (i == 0) g_button_record_pressed = true;
            else if (i == 1) oled_next_mode();
            else if (i == 2) experiment_trigger_stimulus();
        }
    }
}

static void start_recording(void)
{
    g_app_state = APP_STATE_ARMING;
    oled_show_message("ARMING...", 2000);

    /* Initialize subsystems */
    ads1256_init();
    ina333_init();
    spike_detect_init();
    spike_classify_init();
    slow_wave_init();

    /* Auto-range: collect 5 s of samples */
    ads1256_start_continuous();
    g_peak_amplitude_window = 0;
    uint32_t range_start = HAL_GetTick();
    while (HAL_GetTick() - range_start < 5000) {
        if (ads1256_sample_available()) {
            int32_t raw = ads1256_read_sample(100);
            float ina_g = ina333_get_gain_value();
            float v = ads1256_to_volts(raw, 6, ina_g) * 1000.0f;  /* mV */
            if (fabsf(v) > g_peak_amplitude_window)
                g_peak_amplitude_window = fabsf(v);
        }
    }
    /* Auto-range based on peak */
    ina333_auto_range(g_peak_amplitude_window / 1000.0f);  /* convert to V */
    ads1256_set_ina_gain(ina333_get_gain_value());

    /* Stop continuous, restart with new gain */
    ads1256_stop_continuous();
    HAL_Delay(10);

    /* Start SD session */
    if (sd_logger_card_present()) {
        sd_logger_start_session();
        oled_show_message("RECORDING", 1000);
    } else {
        oled_show_message("NO SD!", 2000);
        /* Record without SD */
    }

    /* Reset counters */
    g_event_count = g_ap_count = g_vp_count = g_art_count = 0;
    g_sample_idx = 0;
    g_session_start_ms = HAL_GetTick();

    /* Start continuous acquisition */
    ads1256_start_continuous();
    g_app_state = APP_STATE_RECORDING;
    power_manager_set_state(PWR_RECORDING);

    /* Notify ESP32 */
    esp32_link_send_status(power_manager_get_battery_voltage(),
                          ina333_get_gain_value(), "REC");
}

static void stop_recording(void)
{
    g_app_state = APP_STATE_STOPPING;
    ads1256_stop_continuous();
    sd_logger_stop_session();
    power_manager_set_state(PWR_IDLE);
    oled_show_message("SAVED", 2000);
    esp32_link_send_status(power_manager_get_battery_voltage(),
                          ina333_get_gain_value(), "IDLE");
    g_app_state = APP_STATE_IDLE;
}

static void process_sample(void)
{
    if (!ads1256_sample_available()) return;

    int32_t raw = ads1256_read_sample(100);
    float ina_g = ina333_get_gain_value();
    float v = ads1256_to_volts(raw, 6, ina_g) * 1000.0f;  /* mV */

    uint32_t ts = HAL_GetTick() - g_session_start_ms;
    int32_t idx = g_sample_idx;
    g_sample_idx++;

    /* Feed spike detector */
    spike_detect_feed(v, ts, idx);

    /* Feed slow-wave analyzer */
    slow_wave_feed(v, ts);

    /* Log to SD */
    sd_logger_log_sample(idx, v, ts);

    /* Send sample to ESP32 (decimated to ~60 Hz for display) */
    if (HAL_GetTick() - g_last_sample_send_ms > 16) {
        esp32_link_send_sample(v, ts, ina_g);
        g_last_sample_send_ms = HAL_GetTick();
    }

    /* Auto-range check (every 10 s) */
    if (HAL_GetTick() - g_last_autorange_ms > 10000) {
        float peak = spike_detect_get_threshold() - spike_detect_get_baseline();
        if (ina333_auto_range(peak / 1000.0f)) {
            ads1256_set_ina_gain(ina333_get_gain_value());
        }
        g_last_autorange_ms = HAL_GetTick();
    }

    /* Process detected events */
    spike_event_t event;
    while (spike_detect_get_event(&event)) {
        /* Classify with CNN */
        spike_classify_event(&event);
        g_event_count++;
        switch (event.classification) {
            case EVENT_AP:    g_ap_count++;    break;
            case EVENT_VP:     g_vp_count++;    break;
            case EVENT_ARTIFACT: g_art_count++; break;
            default: break;
        }

        /* Log + stream */
        sd_logger_log_event(&event);
        esp32_link_send_event(&event);
    }

    /* Process slow-wave results */
    swp_result_t swp;
    if (slow_wave_get_result(&swp)) {
        sd_logger_log_swp(&swp);
        esp32_link_send_swp(&swp);
    }
}

static void update_display(void)
{
    if (HAL_GetTick() - g_last_display_ms < 50) return;  /* 20 Hz */
    g_last_display_ms = HAL_GetTick();

    oled_update(
        spike_detect_get_display_value(),
        spike_detect_get_threshold(),
        spike_detect_get_baseline(),
        g_sample_idx,
        g_event_count, g_ap_count, g_vp_count, g_art_count,
        power_manager_get_battery_voltage(),
        ina333_get_gain_value(),
        g_app_state == APP_STATE_RECORDING,
        experiment_current()
    );
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    gpio_init();
    spi1_init();
    spi2_init();
    i2c1_init();
    usart1_init();
    adc1_init();

    /* Initialize subsystems */
    power_manager_init();
    oled_init();
    oled_show_message("PHYTO PULSE", 2000);
    bme280_init();
    sd_logger_init();
    esp32_link_init();

    /* Main loop */
    while (1) {
        buttons_scan();

        if (g_button_record_pressed) {
            g_button_record_pressed = false;
            if (g_app_state == APP_STATE_IDLE) {
                start_recording();
            } else if (g_app_state == APP_STATE_RECORDING) {
                stop_recording();
            }
        }

        if (g_app_state == APP_STATE_RECORDING) {
            process_sample();
        }

        update_display();
        esp32_link_process();

        /* Low-power when idle */
        if (g_app_state == APP_STATE_IDLE) {
            __WFI();
        }
    }
}

/* Interrupt handlers */
void EXTI15_10_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_15);
}

void DMA1_Channel2_IRQHandler(void)
{
    HAL_DMA_IRQHandler(hspi1.hdmarx);
}

void HardFault_Handler(void)
{
    while (1) { }
}