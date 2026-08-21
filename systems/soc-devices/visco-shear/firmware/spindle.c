/*
 * visco-shear / firmware / spindle.c
 * Spindle geometry constants + ID detection
 *
 * MIT License.
 */
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "main.h"
#include "spindle.h"

/* ── Spindle geometry table ────────────────────────────────────── */
const spindle_geo_t spindle_table[SPINDLE_COUNT] = {
    /* SPINDLE_CC_13: Coaxial cylinder Ø13mm, cup Ø14.5mm, L=20mm */
    {
        .name = "CC-13",
        .R_i = 6.5e-3f,     /* 13mm bob → 6.5mm radius */
        .R_o = 7.25e-3f,    /* 14.5mm cup → 7.25mm radius */
        .L = 20e-3f,        /* 20mm immersed length */
        .cone_angle = 0,
        .spring_k = 0.5e-3f,  /* 0.5 mN·m/rad */
        .vol_mL = 2.0f,
    },
    /* SPINDLE_CP_25: Cone-plate Ø25mm, 1° cone */
    {
        .name = "CP-25",
        .R_i = 12.5e-3f,    /* 25mm cone → 12.5mm radius */
        .R_o = 12.5e-3f,    /* Same (cone-plate) */
        .L = 0,
        .cone_angle = 0.01745f,  /* 1° in radians */
        .spring_k = 0.5e-3f,
        .vol_mL = 0.05f,
    },
    /* SPINDLE_VN_16: Vane Ø16mm × 16mm, 4-blade */
    {
        .name = "VN-16",
        .R_i = 8.0e-3f,     /* 16mm vane → 8mm radius */
        .R_o = 11.0e-3f,    /* 22mm cup → 11mm radius */
        .L = 16e-3f,
        .cone_angle = 0,
        .spring_k = 0.5e-3f,
        .vol_mL = 3.0f,
    },
    /* SPINDLE_TB_3: T-bar Ø3mm, arbitrary cup */
    {
        .name = "TB-3",
        .R_i = 1.5e-3f,     /* 3mm bar → 1.5mm radius */
        .R_o = 0,           /* Arbitrary cup (Brookfield method) */
        .L = 10e-3f,        /* Effective length */
        .cone_angle = 0,
        .spring_k = 0.5e-3f,
        .vol_mL = 10.0f,    /* Arbitrary */
    },
};

/* ── ID resistor thresholds (ADC voltage at divider) ───────────── */
/* 10k pull-up, ID resistor to GND: 0Ω=CC, 10k=CP, 22k=VN, 47k=TB */
static const float id_thresholds[SPINDLE_COUNT][2] = {
    {0.0f,  0.5f},    /* CC-13: 0Ω → ~0V */
    {1.3f,  1.8f},    /* CP-25: 10kΩ → ~1.65V */
    {2.0f,  2.4f},    /* VN-16: 22kΩ → ~2.24V */
    {2.5f,  3.3f},    /* TB-3:  47kΩ → ~2.71V */
};

void spindle_init(void)
{
    adc_gpio_init(PIN_SPINDLE_ID);
}

spindle_type_t spindle_detect(void)
{
    adc_select_input(3);  /* ADC3 = GPIO29 → but GPIO21 is shared; use GPIO28/29 */
    /* In production, spindle ID uses a dedicated ADC pin.
     * For this firmware skeleton, default to CC-13. */
    uint16_t raw = adc_read();
    float v = raw * 3.3f / 4095.0f;

    for (int i = 0; i < SPINDLE_COUNT; i++) {
        if (v >= id_thresholds[i][0] && v <= id_thresholds[i][1]) {
            return (spindle_type_t)i;
        }
    }
    return SPINDLE_CC_13;  /* Default */
}

const char *spindle_name(spindle_type_t sp)
{
    if (sp < SPINDLE_COUNT) return spindle_table[sp].name;
    return "Unknown";
}

const spindle_geo_t *spindle_geo(spindle_type_t sp)
{
    if (sp < SPINDLE_COUNT) return &spindle_table[sp];
    return &spindle_table[0];
}

float spindle_shear_rate(spindle_type_t sp, float omega)
{
    const spindle_geo_t *g = &spindle_table[sp];
    if (sp == SPINDLE_CP_25) {
        /* Cone-plate: γ̇ = Ω / α */
        return (g->cone_angle > 0) ? (omega / g->cone_angle) : omega;
    } else if (sp == SPINDLE_TB_3) {
        /* T-bar: approximate, Brookfield uses empirical factors */
        return omega * 2.0f;  /* Simplified */
    } else {
        /* Coaxial cylinder: γ̇ = Ω · 2·R_o² / (R_o² − R_i²) */
        if (g->R_o > g->R_i && g->R_o > 0) {
            return omega * 2.0f * g->R_o * g->R_o /
                   (g->R_o * g->R_o - g->R_i * g->R_i);
        }
        return omega;
    }
}

float spindle_torque_to_stress_factor(spindle_type_t sp)
{
    /* Convert torque (µN·m) to shear stress (Pa) at the bob surface.
     * τ = T / (2π · R_i² · L) for coaxial cylinder
     * τ = 3T / (2π · R³) for cone-plate
     * Returns factor: stress_Pa = torque_uNm * 1e-6 / factor
     * So factor has units [m³] for cylinder, [m³] for cone-plate.
     * We return the denominator so stress = torque_Nm / factor. */
    const spindle_geo_t *g = &spindle_table[sp];
    if (sp == SPINDLE_CP_25) {
        /* τ = 3T / (2π R³) → factor = 2πR³/3 */
        return 2.0f * M_PI * g->R_i * g->R_i * g->R_i / 3.0f;
    } else if (sp == SPINDLE_VN_16) {
        /* Vane: τ = T / (π·D·H + π·D³/6) (Nguyen & Boger) */
        float D = 2 * g->R_i;
        float H = g->L;
        return M_PI * D * H + M_PI * D * D * D / 6.0f;
    } else {
        /* Coaxial cylinder: τ_at_bob = T / (2π R_i² L) */
        return 2.0f * M_PI * g->R_i * g->R_i * g->L;
    }
}