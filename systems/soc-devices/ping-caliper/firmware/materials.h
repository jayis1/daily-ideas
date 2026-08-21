/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * materials.h — Material longitudinal-wave velocity database
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef MATERIALS_H
#define MATERIALS_H

#include "config.h"

typedef struct {
    char     name[MATERIAL_NAME_MAX];
    uint32_t velocity_mps;   /* longitudinal wave velocity at ~20 °C */
    uint32_t shear_velocity_mps;  /* shear velocity (for angle-beam probes) */
    float    density_gcc;     /* density (g/cm³) — for acoustic impedance calc */
} material_t;

void materials_init(void);
uint8_t materials_count(void);
const material_t *materials_get(uint8_t idx);
int8_t materials_find_by_name(const char *name);
uint8_t materials_set_default(uint8_t idx);
uint8_t materials_get_default_idx(void);

/* Edit a custom material slot (indices ≥ MATERIAL_COUNT_BUILTIN). */
uint8_t materials_add_custom(const char *name, uint32_t vel_mps,
                               uint32_t shear_mps, float density);
void materials_save_to_flash(void);
void materials_load_from_flash(void);

#endif /* MATERIALS_H */