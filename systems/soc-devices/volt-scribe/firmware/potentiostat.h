/*
 * volt-scribe — potentiostat.h
 * Potentiostat control interface
 */

#ifndef POTENTIOSTAT_H
#define POTENTIOSTAT_H

#include "stm32g4xx_hal.h"

/* ── TIA current ranges ───────────────────────────────────────── */
typedef enum {
    TIA_1NA = 0,    /* 1 nA   — Rf = 100 MΩ */
    TIA_10NA,       /* 10 nA  — Rf = 10 MΩ */
    TIA_100NA,      /* 100 nA — Rf = 1 MΩ */
    TIA_1UA,        /* 1 µA   — Rf = 100 kΩ */
    TIA_10UA,       /* 10 µA  — Rf = 10 kΩ */
    TIA_100UA,      /* 100 µA — Rf = 1 kΩ */
    TIA_10MA,       /* 10 mA  — Rf = 100 Ω */
    TIA_RANGE_COUNT
} tia_range_t;

/* ── Global variables ──────────────────────────────────────────── */
extern float eis_ac_amplitude_mv;

/* ── Functions ─────────────────────────────────────────────────── */

void pot_init(void);
void pot_set_voltage(float volts);
float pot_read_current(void);
float pot_read_potential(void);

void pot_set_range(tia_range_t range);
tia_range_t pot_get_range(void);
tia_range_t pot_auto_range(void);
const char *tia_range_name(tia_range_t range);
float tia_rf_value(tia_range_t range);

void pot_cell_enable(int enable);

void pot_eis_set_dc(float volts);
void pot_eis_set_ac_amplitude(float mv_rms);

#endif /* POTENTIOSTAT_H */