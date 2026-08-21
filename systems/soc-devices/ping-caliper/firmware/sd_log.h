/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * sd_log.h — FatFs-based measurement & A-scan logging to MicroSD
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include "config.h"
#include "receiver.h"
#include "thickness.h"
#include "flaw.h"

typedef struct {
    uint32_t sequence;
    uint32_t timestamp;       /* epoch seconds (from ESP32-C3 RTC sync) */
    float    thickness_mm;
    float    tof_ns;
    uint32_t velocity_mps;
    uint8_t  mode;            /* measure_mode_t */
    uint8_t  flaw_detected;
    float    flaw_depth_mm;
    float    flaw_equiv_mm;
    float    gain_db;
    int16_t  battery_pct;
    char     material[MATERIAL_NAME_MAX];
} log_entry_t;

void sd_init(void);
uint8_t sd_present(void);

/* Append a measurement entry to PINGLOG.CSV. */
uint8_t sd_log_measurement(const log_entry_t *entry);

/* Save an A-scan raw capture to a binary file (ASCAN_nnnn.BIN). */
uint8_t sd_log_ascan(const ascan_t *scan, uint32_t seq);

/* Read N most-recent entries (for log browsing on OLED). */
uint8_t sd_log_read_recent(log_entry_t *out, uint8_t max_count);

/* Total count of logged measurements. */
uint32_t sd_log_count(void);

/* Sync & unmount (power-down). */
void sd_sync(void);

#endif /* SD_LOG_H */