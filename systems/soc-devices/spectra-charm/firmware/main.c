/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * STM32G491RET6 Firmware
 *
 * main.c — FreeRTOS task initialization and system entry point
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "stm32g4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include "spectrometer.h"
#include "deconv.h"
#include "matching.h"
#include "baseline.h"
#include "beerlambert.h"
#include "led_driver.h"
#include "flash_store.h"
#include "uart_proto.h"
#include "eeprom.h"
#include "fuel_gauge.h"
#include "power.h"

/* ---- Task Handles ---- */
static TaskHandle_t hSpectrometerTask;
static TaskHandle_t hCommTask;
static TaskHandle_t hUITask;
static TaskHandle_t hPowerTask;

/* ---- Queues ---- */
QueueHandle_t xScanRequestQueue;    /* Scan request messages from ESP32-C3 */
QueueHandle_t xSpectrumResultQueue; /* Spectrum results to ESP32-C3 */
QueueHandle_t xPowerEventQueue;     /* Power management events */

/* ---- Semaphores ---- */
SemaphoreHandle_t xI2CMutex;
SemaphoreHandle_t xSPIMutex;

/* ---- Global State ---- */
typedef struct {
    float absorbance[SPECTRUM_POINTS];  /* 128-point absorbance spectrum */
    float reference[SPECTRUM_POINTS];   /* Current blank reference */
    float dark[SPECTRUM_POINTS];        /* Dark offsets */
    uint8_t scan_count;
    uint8_t library_compounds;
    uint8_t battery_pct;
    bool calibrated;
    bool cuvette_present;
} SystemState_t;

static SystemState_t gState;

/* ---- Peripheral Handles ---- */
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
DAC_HandleTypeDef hdac1;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1;
SPI_HandleTypeDef hspi2;
UART_HandleTypeDef huart1;
OPAMP_HandleTypeDef hopamp1;
OPAMP_HandleTypeDef hopamp2;
IWDG_HandleTypeDef hiwdg;

/* ========================================================================
 * Clock Configuration — 170 MHz from HSI16 + PLL
 * ======================================================================== */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    /* HSI16 as PLL source */
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSI | RCC_OSCILLATORTYPE_LSE;
    osc.HSIState = RCC_HSI_ON;
    osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    osc.LSEState = RCC_LSE_ON;  /* LSE for RTC */
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    osc.PLL.PLLM = 4;    /* HSI16/4 = 4 MHz */
    osc.PLL.PLLN = 85;   /* 4 MHz * 85 = 340 MHz */
    osc.PLL.PLLP = 2;    /* 340/2 = 170 MHz SYSCLK */
    osc.PLL.PLLQ = 4;    /* 340/4 = 85 MHz (USB not used, but keep valid) */
    osc.PLL.PLLR = 2;    /* 170 MHz */
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;   /* 170 MHz */
    clk.APB1CLKDivider = RCC_HCLK_DIV1;    /* 170 MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;    /* 170 MHz */
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);

    /* Enable VDD12 power boost for 170 MHz */
    __HAL_RCC_PWR_CLK_ENABLE();
    HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1_BOOST);
}

/* ========================================================================
 * GPIO Initialization
 * ======================================================================== */
static void GPIO_Init(void)
{
    GPIO_InitTypeDef gpio = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    /* LED control outputs */
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9;  /* UV_LED_EN, WHITE_LED_EN */
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* SPI1: AS7343 — PA6(MISO), PA7(MOSI), PA12(NSS), PA11(SCK) — reassign */
    /* Actually using PA5 as SCK, PA6 MISO, PA7 MOSI, PA4 NSS per pin table */
    gpio.Pin = GPIO_PIN_4 | GPIO_PIN_5;  /* SPI1_NSS (sw), SPI1_SCK (AF) */
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Alternate = GPIO_AF5_SPI1;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* PA6, PA7 — SPI1 MISO/MOSI */
    gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* SPI2: W25Q128 — PB2(MOSI), PB1(MISO), PB3(SCK), PB4(NSS) */
    gpio.Pin = GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3 | GPIO_PIN_4;
    gpio.Alternate = GPIO_AF5_SPI2;
    HAL_GPIO_Init(GPIOB, &gpio);

    /* I2C1: PB5(SDA), PB6(SCL) — EEPROM + Fuel Gauge */
    gpio.Pin = GPIO_PIN_5 | GPIO_PIN_6;
    gpio.Alternate = GPIO_AF4_I2C1;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &gpio);

    /* UART1: PA9(TX), PA10(RX) */
    gpio.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    gpio.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* AS7343 interrupt — PB7 */
    gpio.Pin = GPIO_PIN_7;
    gpio.Mode = GPIO_MODE_IT_FALLING;
    gpio.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOB, &gpio);

    /* Buttons — PC7, PC8 */
    gpio.Pin = GPIO_PIN_7 | GPIO_PIN_8;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &gpio);

    /* Status LEDs — PC11, PC12, PC13 */
    gpio.Pin = GPIO_PIN_11 | GPIO_PIN_12 | GPIO_PIN_13;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &gpio);

    /* ESP32 control — PC9(BOOT), PC10(RST_N) */
    gpio.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOC, &gpio);

    /* Power rail enable — PC6 (SHUTDOWN_N) */
    gpio.Pin = GPIO_PIN_6;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_WriteGPIO(GPIOC, GPIO_PIN_6, GPIO_PIN_SET); /* Rail on */
    HAL_GPIO_Init(GPIOC, &gpio);

    /* Hall sensor — PD2 (cuvette interlock) */
    gpio.Pin = GPIO_PIN_2;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOD, &gpio);
}

/* ========================================================================
 * ADC Configuration — 12-bit, oversampling for 16-bit effective
 * ======================================================================== */
static void ADC_Init(void)
{
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ENABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    hadc1.Init.OversamplingMode = ENABLE;
    hadc1.Init.Oversampling.Ratio = ADC_OVERSAMPLING_RATIO_256;
    hadc1.Init.Oversampling.RightBitShift = ADC_RIGHTBITSHIFT_4; /* 16-bit effective */
    hadc1.Init.Oversampling.TriggeredMode = ADC_OVERSAMPLING_TRIGGEREDMODE_SINGLE;
    HAL_ADC_Init(&hadc1);

    /* Channel 1 — PA0: Photodiode via op-amp */
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_1;
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    ch.SingleDiff = ADC_SINGLE_ENDED;
    ch.OffsetNumber = ADC_OFFSET_NONE;
    HAL_ADC_ConfigChannel(&hadc1, &ch);
}

/* ========================================================================
 * DAC Configuration — LED current control references
 * ======================================================================== */
static void DAC_Init(void)
{
    hdac1.Instance = DAC1;
    HAL_DAC_Init(&hdac1);

    /* Channel 1: White LED current reference — PA4 */
    HAL_DAC_ConfigChannel(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R);
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, 0);
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_1);

    /* Channel 2: UV LED current reference — PA5 */
    HAL_DAC_ConfigChannel(&hdac1, DAC_CHANNEL_2, DAC_ALIGN_12B_R);
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_2, DAC_ALIGN_12B_R, 0);
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_2);
}

/* ========================================================================
 * Internal Op-Amp Configuration — Photodiode Transimpedance
 * ======================================================================== */
static void OpAmp_Init(void)
{
    /* OPAMP1: PA2 (VINP) → internal, gain = x8, output → ADC1_IN1 via internal routing */
    hopamp1.Instance = OPAMP1;
    hopamp1.Init.Mode = OPAMP_STANDALONE_MODE;
    hopamp1.Init.NonInvertingInput = OPAMP_NONINVERTINGINPUT_IO0; /* PA2 */
    hopamp1.Init.InvertingInput = OPAMP_INVERTINGINPUT_INTERNAL;  /* Internal feedback */
    hopamp1.Init.InternalOutput = ENABLE;  /* Route to ADC internally */
    hopamp1.Init.PgaGain = OPAMP_PGA_GAIN_8;
    hopamp1.Init.UserTrimming = OPAMP_TRIMMING_FACTORY;
    HAL_OPAMP_Init(&hopamp1);
    HAL_OPAMP_Start(&hopamp1);

    /* OPAMP2: PC0 (VINP) → backup channel */
    hopamp2.Instance = OPAMP2;
    hopamp2.Init.Mode = OPAMP_STANDALONE_MODE;
    hopamp2.Init.NonInvertingInput = OPAMP_NONINVERTINGINPUT_IO1; /* PC0 */
    hopamp2.Init.InvertingInput = OPAMP_INVERTINGINPUT_INTERNAL;
    hopamp2.Init.InternalOutput = ENABLE;
    hopamp2.Init.PgaGain = OPAMP_PGA_GAIN_8;
    hopamp2.Init.UserTrimming = OPAMP_TRIMMING_FACTORY;
    HAL_OPAMP_Init(&hopamp2);
    HAL_OPAMP_Start(&hopamp2);
}

/* ========================================================================
 * SPI Initialization
 * ======================================================================== */
static void SPI_Init(void)
{
    /* SPI1: AS7343 — Mode 1, 1 MHz */
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_128; /* 170/128 ≈ 1.3 MHz */
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi1);

    /* SPI2: W25Q128 — Mode 0, 10 MHz */
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16; /* 170/16 ≈ 10.6 MHz */
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    HAL_SPI_Init(&hspi2);
}

/* ========================================================================
 * I2C and UART Initialization
 * ======================================================================== */
static void I2C_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x00B03FDB; /* 400 kHz at 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void UART_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart1);
}

/* ========================================================================
 * IWDG Configuration — 4 second timeout
 * ======================================================================== */
static void IWDG_Init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;   /* LSI 32kHz / 64 = 500 Hz */
    hiwdg.Init.Reload = 2000;                    /* 2000 / 500 = 4 seconds */
    HAL_IWDG_Init(&hiwdg);
}

/* ========================================================================
 * Spectrometer Task — Acquire and process spectra
 * ======================================================================== */
static void SpectrometerTask(void *pvParams)
{
    ScanRequest_t req;
    SpectrumResult_t result;
    TickType_t xLastWakeTime;

    for (;;) {
        /* Wait for scan request (block indefinitely) */
        if (xQueueReceive(xScanRequestQueue, &req, portMAX_DELAY) == pdTRUE) {

            /* Check cuvette interlock (hall sensor) */
            gState.cuvette_present = (HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_2) == GPIO_PIN_RESET);
            if (!gState.cuvette_present && req.type != SCAN_TYPE_DARK) {
                result.status = SCAN_ERR_NO_CUVETTE;
                xQueueSend(xSpectrumResultQueue, &result, 100);
                continue;
            }

            /* Perform spectral acquisition */
            switch (req.type) {
            case SCAN_TYPE_DARK:
                Spectrometer_AcquireDark(gState.dark);
                result.status = SCAN_OK;
                break;

            case SCAN_TYPE_BLANK:
                Spectrometer_AcquireBlank(gState.reference, gState.dark);
                result.status = SCAN_OK;
                break;

            case SCAN_TYPE_SAMPLE:
                Spectrometer_AcquireSample(gState.absorbance, gState.reference,
                                          gState.dark, &result);
                /* Run spectral matching */
                if (result.status == SCAN_OK) {
                    Matching_FindBest(gState.absorbance, &result.match);
                    /* Beer-Lambert concentration if compound found */
                    if (result.match.compound_id != COMPOUND_NONE) {
                        result.concentration = BeerLambert_Calculate(
                            gState.absorbance,
                            &result.match
                        );
                    }
                }
                break;

            default:
                result.status = SCAN_ERR_INVALID;
                break;
            }

            gState.scan_count++;
            result.scan_number = gState.scan_count;

            /* Send result to comm task */
            xQueueSend(xSpectrumResultQueue, &result, 100);
        }

        /* Kick watchdog */
        HAL_IWDG_Refresh(&hiwdg);
    }
}

/* ========================================================================
 * Communication Task — UART protocol to ESP32-C3
 * ======================================================================== */
static void CommTask(void *pvParams)
{
    SpectrumResult_t result;
    UartPacket_t txPkt;

    for (;;) {
        /* Wait for spectrum results */
        if (xQueueReceive(xSpectrumResultQueue, &result, portMAX_DELAY) == pdTRUE) {
            /* Encode result into UART protocol packet */
            UartProto_EncodeResult(&result, &txPkt);
            /* Transmit to ESP32-C3 */
            HAL_UART_Transmit(&huart1, (uint8_t *)&txPkt, txPkt.length, 100);
        }

        /* Check for incoming UART data from ESP32-C3 */
        /* (DMA-based receive handled in interrupt, routes to xScanRequestQueue) */
    }
}

/* ========================================================================
 * Power Management Task
 * ======================================================================== */
static void PowerTask(void *pvParams)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();

    for (;;) {
        /* Read battery percentage from fuel gauge */
        gState.battery_pct = FuelGauge_GetSOC(&hi2c1);

        /* Check for low battery */
        if (gState.battery_pct < 5) {
            Power_EnterDeepSleep();
        }

        /* Check cuvette present state */
        gState.cuvette_present = (HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_2) == GPIO_PIN_RESET);

        /* Run every 5 seconds */
        vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(5000));
    }
}

/* ========================================================================
 * Main Entry Point
 * ======================================================================== */
int main(void)
{
    /* HAL initialization */
    HAL_Init();
    SystemClock_Config();

    /* Peripheral init */
    GPIO_Init();
    ADC_Init();
    DAC_Init();
    OpAmp_Init();
    SPI_Init();
    I2C_Init();
    UART_Init();
    IWDG_Init();

    /* Initialize state */
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        gState.absorbance[i] = 0.0f;
        gState.reference[i] = 1.0f;
        gState.dark[i] = 0.0f;
    }
    gState.scan_count = 0;
    gState.calibrated = false;
    gState.cuvette_present = false;
    gState.battery_pct = 100;

    /* Load calibration from EEPROM */
    EEPROM_LoadCalibration(&hi2c1, &gState);

    /* Load spectral library count from SPI flash */
    gState.library_compounds = FlashStore_GetLibraryCount(&hspi2);

    /* Create synchronization primitives */
    xI2CMutex = xSemaphoreCreateMutex();
    xSPIMutex = xSemaphoreCreateMutex();
    xScanRequestQueue = xQueueCreate(4, sizeof(ScanRequest_t));
    xSpectrumResultQueue = xQueueCreate(4, sizeof(SpectrumResult_t));
    xPowerEventQueue = xQueueCreate(8, sizeof(uint8_t));

    /* Enable NVIC for AS7343 interrupt (PB7) */
    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);

    /* Create tasks */
    xTaskCreate(SpectrometerTask, "Spectr", 2048, NULL, 3, &hSpectrometerTask);
    xTaskCreate(CommTask, "Comm", 1024, NULL, 2, &hCommTask);
    xTaskCreate(PowerTask, "Power", 512, NULL, 1, &hPowerTask);

    /* Signal ESP32-C3 that spectrometer MCU is ready */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_10, GPIO_PIN_SET); /* RST_N high = running */

    /* Start scheduler */
    vTaskStartScheduler();

    /* Should never reach here */
    for (;;) {
        HAL_IWDG_Refresh(&hiwdg);
    }
}

/* ========================================================================
 * Interrupt Handlers
 * ======================================================================== */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    if (GPIO_Pin == GPIO_PIN_7) {
        /* AS7343 data ready — notify spectrometer task */
        vTaskNotifyGiveFromISR(hSpectrometerTask, &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

void HardFault_Handler(void)
{
    /* Flash red LED rapidly */
    while (1) {
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_12); /* Red LED */
        for (volatile int i = 0; i < 200000; i++);
    }
}

void MemManage_Handler(void)
{
    HardFault_Handler();
}

void BusFault_Handler(void)
{
    HardFault_Handler();
}