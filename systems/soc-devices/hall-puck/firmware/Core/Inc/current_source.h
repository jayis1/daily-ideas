/*
 * hall-puck / firmware / Core / Inc / current_source.h
 * Programmable precision current source (Howland pump)
 *
 * Uses STM32 internal DAC1 → OPA2188 Howland current pump
 * Two ranges: 1µA–100µA (low) and 100µA–10mA (high)
 *
 * MIT License.
 */
#ifndef CURRENT_SOURCE_H
#define CURRENT_SOURCE_H

#include <stdint.h>
#include <stdbool.h>

/* Current ranges */
#define I_RANGE_LOW     0   /* 1µA – 100µA */
#define I_RANGE_HIGH    1   /* 100µA – 10mA */

/* Limits */
#define I_MIN_UA        1.0f        /* 1 µA */
#define I_MAX_MA        10.0f       /* 10 mA */

typedef enum {
    I_SRC_OK = 0,
    I_SRC_ERR_RANGE = -1,
    I_SRC_ERR_DAC = -2,
} i_src_err_t;

/* Initialize current source (DAC + GPIO) */
i_src_err_t current_source_init(void);

/* Set current in mA (auto-selects range) */
i_src_err_t current_source_set(float current_ma);

/* Enable current output */
void current_source_enable(void);

/* Disable current output */
void current_source_disable(void);

/* Get actual current (from sense resistor reading) */
float current_source_read_actual_ma(void);

/* Get current range (0=low, 1=high) */
uint8_t current_source_get_range(void);

/* Get programmed current in mA */
float current_source_get_set_ma(void);

#endif /* CURRENT_SOURCE_H */