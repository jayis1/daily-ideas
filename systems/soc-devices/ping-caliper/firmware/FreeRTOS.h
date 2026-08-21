/*
 * FreeRTOS minimal headers for Ping Caliper (STM32G474)
 *
 * These are simplified declarations sufficient for the Ping Caliper build.
 * A real build links against the official FreeRTOS kernel source.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef FREERTOS_H
#define FREERTOS_H

#include <stdint.h>
#include <stddef.h>

/* Type definitions (matches FreeRTOS API) */
typedef void *TaskHandle_t;
typedef void *QueueHandle_t;
typedef void *SemaphoreHandle_t;
typedef uint32_t TickType_t;
typedef int32_t BaseType_t;
#define pdTRUE        ((BaseType_t)1)
#define pdFALSE       ((BaseType_t)0)
#define pdPASS        (0)
#define pdFAIL        (0)

/* Task creation */
BaseType_t xTaskCreate(void (*pxTask)(void *), const char *name,
                        uint16_t stack, void *arg, uint8_t prio,
                        TaskHandle_t *handle);

/* Queues */
QueueHandle_t xQueueCreate(uint8_t len, uint8_t sz);
BaseType_t xQueueSend(QueueHandle_t q, const void *item, TickType_t to);
BaseType_t xQueueReceive(QueueHandle_t q, void *item, TickType_t to);

/* Semaphores */
SemaphoreHandle_t xSemaphoreCreateMutex(void);
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t to);
BaseType_t xSemaphoreGive(SemaphoreHandle_t s);

/* Scheduler */
void vTaskStartScheduler(void);
void vTaskDelay(TickType_t ticks);
void vTaskDelayUntil(TickType_t *prev, TickType_t ticks);
TickType_t xTaskGetTickCount(void);
BaseType_t xTaskGetSchedulerState(void);

/* Tick conversion */
#define pdMS_TO_TICKS(ms)   ((TickType_t)((ms) / portTICK_PERIOD_MS))
#define portTICK_PERIOD_MS (1000U / configTICK_RATE_HZ)

/* Task notifications (used by DMA ISR) */
BaseType_t xTaskNotifyGive(TaskHandle_t h);

/* Scheduler states */
#define taskSCHEDULER_NOT_STARTED 0

/* Hooks */
extern void vApplicationStackOverflowHook(TaskHandle_t, char *);
extern void vApplicationMallocFailedHook(void);
extern void vApplicationIdleHook(void);

#endif /* FREERTOS_H */