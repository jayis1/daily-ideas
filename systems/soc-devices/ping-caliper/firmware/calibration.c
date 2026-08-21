/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * calibration.c — Zero-probe (delay-line) and velocity calibration
 *
 * Zero-probe calibration: with the probe coupled to a known-thickness
 * reference block (or in air for delay-line probes), determine the probe's
 * inherent delay (zero offset) so it can be subtracted from all measurements.
 *
 * Velocity calibration: measure the TOF through a block of known thickness
 * and solve for the material velocity: v = 2 * d / Δt.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "calibration.h"
#include "thickness.h"
#include "materials.h"
#include <string.h>

static calibration_t g_cal;

void calibration_init(void)
{
    memset(&g_cal, 0, sizeof(g_cal));
    g_cal.state = CAL_STATE_IDLE;
    g_cal.zero_offset_ns = 0;
    g_cal.measured_velocity_mps = 5920;
    g_cal.reference_thickness_mm = 0.0f;
    g_cal.gain_offset_db = 0.0f;
}

void calibration_start_zero(void)
{
    g_cal.state = CAL_STATE_ZERO_PROBE;
}

void calibration_start_velocity(float known_thickness_mm)
{
    g_cal.state = CAL_STATE_VELOCITY;
    g_cal.reference_thickness_mm = known_thickness_mm;
}

void calibration_update(const ascan_t *scan, calibration_t *cal)
{
    if (!scan || !cal) return;

    switch (cal->state) {
    case CAL_STATE_ZERO_PROBE: {
        /* In zero-probe mode the probe is coupled to a reference block of
         * known thickness. We measure the surface-to-back-wall TOF and
         * subtract the known travel time; the remainder is the probe delay.
         * If coupled to air (delay-line probe), there is no back-wall echo;
         * we instead use the initial pulse ring-down as the zero reference. */
        thickness_result_t thk;
        thk.velocity_mps = cal->measured_velocity_mps;
        thk.mode = MEASURE_MODE_PULSE_ECHO;
        thickness_compute(scan, &thk, &thk);
        if (thk.valid) {
            /* Expected TOF for the reference: 2 * d / v (in ns) */
            float expected_ns = 2.0f * cal->reference_thickness_mm /
                                (float)cal->measured_velocity_mps * 1.0e6f;
            cal->zero_offset_ns = (uint16_t)(thk.tof_ns - expected_ns);
            if (cal->zero_offset_ns > 5000) cal->zero_offset_ns = 0;
        }
        cal->state = CAL_STATE_DONE;
        break;
    }
    case CAL_STATE_VELOCITY: {
        /* Measure TOF through a known-thickness block and solve for v.
         * v = 2 * d / (Δt − zero_offset) */
        thickness_result_t thk;
        thk.velocity_mps = 5920;  /* dummy; we're solving for this */
        thk.mode = MEASURE_MODE_PULSE_ECHO;
        thickness_compute(scan, &thk, &thk);
        if (thk.valid && cal->reference_thickness_mm > 0.0f) {
            float tof_s = (thk.tof_ns - cal->zero_offset_ns) / 1.0e9f;
            if (tof_s > 0.0f) {
                cal->measured_velocity_mps =
                    (uint32_t)((2.0f * cal->reference_thickness_mm /
                                tof_s) + 0.5f);
            }
        }
        cal->state = CAL_STATE_DONE;
        break;
    }
    case CAL_STATE_GAIN: {
        /* Gain calibration: measure a reference reflector at a known depth
         * and set the gain offset so its amplitude reads 80% full-scale. */
        /* Simplified: find max amplitude in the window. */
        uint16_t max_v = 0;
        for (uint16_t i = 0; i < scan->count; i++)
            if (scan->envelope[i] > max_v) max_v = scan->envelope[i];
        float amp_frac = (float)max_v / (float)ADC_MAX;
        if (amp_frac > 0.01f) {
            cal->gain_offset_db = 20.0f * log10f(0.8f / amp_frac);
        }
        cal->state = CAL_STATE_DONE;
        break;
    }
    default:
        break;
    }
}

void calibration_save(const calibration_t *cal)
{
    /* Persist to flash (separate page from materials). Simplified. */
    FLASH->KEYR = 0x45670123U;
    FLASH->KEYR = 0xCDEF89ABU;
    FLASH->CR |= FLASH_CR_PER;
    FLASH->AR = 0x08078000U;
    FLASH->CR |= FLASH_CR_STTR;
    while (FLASH->SR & FLASH_CR_STRT) { }
    FLASH->CR &= ~FLASH_CR_PER;
    FLASH->CR |= FLASH_CR_PG;
    uint16_t *dst = (uint16_t *)0x08078000U;
    uint16_t *src = (uint16_t *)cal;
    uint16_t words = sizeof(calibration_t) / 2;
    for (uint16_t i = 0; i < words; i++) {
        dst[i] = src[i];
        while (FLASH->SR & FLASH_SR_BSY) { }
    }
    FLASH->CR &= ~FLASH_CR_PG;
    FLASH->CR |= FLASH_CR_LOCK;
}

void calibration_load(calibration_t *cal)
{
    if (!cal) return;
    uint16_t *src = (uint16_t *)0x08078000U;
    if (src[0] == 0xFFFF) {   /* empty flash */
        calibration_init();
        *cal = g_cal;
        return;
    }
    uint16_t *dst = (uint16_t *)cal;
    uint16_t words = sizeof(calibration_t) / 2;
    for (uint16_t i = 0; i < words; i++)
        dst[i] = src[i];
    cal->state = CAL_STATE_IDLE;
    g_cal = *cal;
}

const calibration_t *calibration_get(void) { return &g_cal; }