/* freertos headers — stubs for host simulation */
#pragma once
#include <stdint.h>
#include <time.h>

typedef int TickType_t;
#define pdMS_TO_TICKS(ms) (ms)
#define portMAX_DELAY 0xFFFFFFFF
static inline TickType_t xTaskGetTickCount(void) { return 0; }
static inline void vTaskDelay(TickType_t t) { (void)t; }
static inline void vTaskDelayUntil(TickType_t *last, TickType_t period) { (void)last; (void)period; }