/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * receiver.h — ADC capture of envelope (ADC1) and RF (ADC2)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef RECEIVER_H
#define RECEIVER_H

#include "config.h"

typedef struct {
    uint16_t window_us;         /* capture window length (µs)            */
    uint16_t sample_count;      /* number of samples (window × 5)       */
    uint8_t  source;            /* 0=env only, 1=RF only, 2=both        */
    uint8_t  trigger_channel;   /* 0=envelope, 1=RF (for auto-trigger)   */
} rx_config_t;

/* Acquired A-scan (double-buffered; filled by DMA) */
typedef struct {
    uint16_t envelope[MAX_SAMPLES];   /* ADC1 envelope samples (12-bit) */
    uint16_t rf[MAX_SAMPLES];         /* ADC2 RF samples (12-bit, if enabled) */
    uint16_t count;                    /* number of valid samples          */
    uint32_t timestamp_us;            /* capture timestamp (from HRTIM)   */
    uint8_t  valid;                    /* 1 = buffer ready for processing  */
} ascan_t;

void receiver_init(void);
void rx_configure(const rx_config_t *cfg);
void rx_get_config(rx_config_t *cfg);

/* Start continuous capture triggered by the pulser timer.
 * Each completed buffer raises a notification to the process task. */
void rx_start_continuous(void);
void rx_stop_continuous(void);

/* Single-shot capture (blocks up to window_us + margin). Returns 1 on ok. */
uint8_t rx_capture_single(ascan_t *out);

/* Get the latest completed A-scan (non-blocking; returns 1 if a new one
 * is available, 0 otherwise). */
uint8_t rx_get_latest(ascan_t *out);

#endif /* RECEIVER_H */