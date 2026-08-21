/*
 * Hive Mind — Main Entry Point
 * STM32WL55JC solar-powered beehive health monitor
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include <stdio.h>
#include <string.h>
#include "main.h"
#include "weight_sensor.h"
#include "temp_chain.h"
#include "acoustic_analyzer.h"
#include "bee_counter.h"
#include "bme280_driver.h"
#include "oled_display.h"
#include "lorawan_uplink.h"
#include "power_manager.h"
#include "hive_health.h"

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* Shared sensor data (protected by mutex) */
static sensor_data_t g_sensor_data;
static SemaphoreHandle_t g_data_mutex;

/* Acoustic classification result */
static volatile acoustic_class_t g_acoustic_class = AC_NORMAL;
static volatile uint16_t g_dominant_freq_hz = 0;

/* Bee traffic counters */
static volatile uint16_t g_bee_count_in = 0;
static volatile uint16_t g_bee_count_out = 0;

/* Console handle */
extern UART_HandleTypeDef hlpuart1;

/* ------------------------------------------------------------------ */
/* FreeRTOS Tasks                                                      */
/* ------------------------------------------------------------------ */

static void sensor_task(void *pvParameters)
{
    (void)pvParameters;

    /* Wait for sensor stabilization */
    vTaskDelay(pdMS_TO_TICKS(2000));

    /* Tare the load cell on startup */
    weight_sensor_tare();

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(30000); /* 30 s */

    for (;;) {
        float weight_g = weight_sensor_read_grams();
        float temps[3];
        float ambient_t, ambient_h, ambient_p;

        temp_chain_read_all(temps);
        bme280_read(&ambient_t, &ambient_h, &ambient_p);
        float vbat = power_manager_read_battery();
        float vsolar = power_manager_read_solar();

        if (xSemaphoreTake(g_data_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            g_sensor_data.weight_g = weight_g;
            g_sensor_data.temp_floor = temps[0];
            g_sensor_data.temp_mid = temps[1];
            g_sensor_data.temp_crown = temps[2];
            g_sensor_data.ambient_t = ambient_t;
            g_sensor_data.ambient_h = ambient_h;
            g_sensor_data.ambient_p = ambient_p;
            g_sensor_data.vbat = vbat;
            g_sensor_data.vsolar = vsolar;
            g_sensor_data.acoustic_class = g_acoustic_class;
            g_sensor_data.dominant_freq = g_dominant_freq_hz;
            g_sensor_data.bee_in = g_bee_count_in;
            g_sensor_data.bee_out = g_bee_count_out;

            /* Compute health score */
            g_sensor_data.health_score = hive_health_compute(&g_sensor_data);

            xSemaphoreGive(g_data_mutex);
        }

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

static void acoustic_task(void *pvParameters)
{
    (void)pvParameters;

    vTaskDelay(pdMS_TO_TICKS(5000));

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(120000); /* 2 min */

    for (;;) {
        acoustic_result_t result = acoustic_analyzer_classify();
        g_acoustic_class = result.cls;
        g_dominant_freq_hz = result.dominant_freq_hz;

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

static void bee_counter_task(void *pvParameters)
{
    (void)pvParameters;

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(240000); /* 4 min */

    for (;;) {
        bee_counts_t counts = bee_counter_count(30000); /* 30 s window */
        g_bee_count_in = counts.in_count;
        g_bee_count_out = counts.out_count;

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

static void uplink_task(void *pvParameters)
{
    (void)pvParameters;

    vTaskDelay(pdMS_TO_TICKS(10000)); /* Wait for LoRaWAN join */

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(900000); /* 15 min */

    for (;;) {
        sensor_data_t snapshot;
        if (xSemaphoreTake(g_data_mutex, pdMS_TO_TICKS(500)) == pdTRUE) {
            snapshot = g_sensor_data;
            xSemaphoreGive(g_data_mutex);
        } else {
            vTaskDelayUntil(&xLastWakeTime, xFrequency);
            continue;
        }

        lorawan_send(&snapshot);

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

static void display_task(void *pvParameters)
{
    (void)pvParameters;

    oled_display_init();

    for (;;) {
        /* Display is only active after button press */
        if (power_manager_user_button_pressed()) {
            sensor_data_t snapshot;
            if (xSemaphoreTake(g_data_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                snapshot = g_sensor_data;
                xSemaphoreGive(g_data_mutex);
            } else {
                vTaskDelay(pdMS_TO_TICKS(100));
                continue;
            }

            oled_display_show(&snapshot);

            /* Keep display on for 10 seconds */
            vTaskDelay(pdMS_TO_TICKS(10000));
            oled_display_off();
        }

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void)
{
    /* HAL init */
    HAL_Init();
    SystemClock_Config();

    /* Low-level hardware init */
    MX_GPIO_Init();
    MX_I2C1_Init();
    MX_LPUART1_UART_Init();
    MX_SPI2_Init();
    MX_I2S2_Init();
    MX_ADC_Init();
    MX_RTC_Init();

    /* Sensor initialization */
    power_manager_init();
    bme280_init();
    weight_sensor_init();
    temp_chain_init();
    bee_counter_init();
    acoustic_analyzer_init();

    /* Create mutex for shared data */
    g_data_mutex = xSemaphoreCreateMutex();

    /* Create FreeRTOS tasks */
    xTaskCreate(sensor_task,    "Sensors",  512, NULL, 2, NULL);
    xTaskCreate(acoustic_task,  "Acoustic", 1024, NULL, 3, NULL);
    xTaskCreate(bee_counter_task, "Bees",    256, NULL, 2, NULL);
    xTaskCreate(uplink_task,    "Uplink",   512, NULL, 1, NULL);
    xTaskCreate(display_task,   "Display",  256, NULL, 0, NULL);

    /* Start scheduler */
    vTaskStartScheduler();

    /* Should never reach here */
    for (;;) {}
}

/* ------------------------------------------------------------------ */
/* System Clock Configuration                                          */
/* ------------------------------------------------------------------ */

void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

    /* Configure LSE for RTC */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_LSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.LSEState = RCC_LSE_ON;
    RCC_OscInitStruct.HSEDiv = RCC_HSE_DIV2; /* 32 MHz / 2 = 16 MHz HSE */
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = RCC_PLLM_DIV2;
    RCC_OscInitStruct.PLL.PLLN = 6;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);

    PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_RTC | RCC_PERIPHCLK_LPUART1;
    PeriphClkInit.RTCClockSelection = RCC_RTCCLKSOURCE_LSE;
    PeriphClkInit.Lpuart1ClockSelection = RCC_LPUART1CLKSOURCE_PCLK1;
    HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);
}

/* ------------------------------------------------------------------ */
/* Fault Handlers                                                       */
/* ------------------------------------------------------------------ */

void HardFault_Handler(void)
{
    while (1) {
        /* Blink red LED rapidly */
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, GPIO_PIN_RESET);
        HAL_Delay(100);
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, GPIO_PIN_SET);
        HAL_Delay(100);
    }
}

void MemManage_Handler(void)
{
    while (1);
}

void BusFault_Handler(void)
{
    while (1);
}