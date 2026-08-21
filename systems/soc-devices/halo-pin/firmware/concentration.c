/*
 * concentration.c — number + mass concentration computation
 *
 * For each bin i with midpoint diameter d_i (µm) and count N_i:
 *   number_conc_i = N_i / V  (#/L)
 *   mass_i = N_i * (π/6) * (d_i/1e4)^3 * ρ * 1e6  (µg per particle)
 *          where d_i in cm = d_i_µm / 1e4
 *                ρ in g/cm³
 *                volume = (π/6)·d³ (cm³) → mass = ρ·V (g) → ×1e6 = µg
 *   PMx = Σ mass_i for bins with d_i ≤ x µm
 *
 * Hygroscopic growth (κ-Köhler):
 *   d_wet = d_dry · (1 + κ·aw/(1−aw))^(1/3)
 *   where aw = RH/100; κ = 0.3 (ammonium sulfate proxy)
 */

#include "concentration.h"
#include "calibration.h"
#include <math.h>
#include <string.h>

#define PI  3.14159265358979f
#define KAPKA_DEFAULT  0.3f
#define RHO_DEFAULT    1.65f    /* g/cm³, typical atmospheric aerosol */

static float rho = RHO_DEFAULT;
static float kappa = KAPKA_DEFAULT;
static bool  hygro = false;
static float num_per_l[NUM_CHANNELS];

void concentration_init(void)
{
    rho = RHO_DEFAULT;
    kappa = KAPKA_DEFAULT;
    hygro = false;
    memset(num_per_l, 0, sizeof(num_per_l));
}

void concentration_set_density(float r) { rho = r; }
float concentration_get_density(void) { return rho; }
void concentration_set_hygroscopic(bool e) { hygro = e; }
bool concentration_get_hygroscopic(void) { return hygro; }

static float hygroscopic_growth(float d_dry_um, float rh_pct)
{
    if (!hygro || rh_pct < 10.0f) return d_dry_um;
    float aw = rh_pct / 100.0f;
    if (aw > 0.98f) aw = 0.98f;   /* cap below 1 to avoid singularity */
    float gf = powf(1.0f + kappa * aw / (1.0f - aw), 1.0f / 3.0f);
    return d_dry_um * gf;
}

void concentration_compute(const uint32_t counts[NUM_CHANNELS],
                            float volume_l,
                            float temp_c, float rh_pct,
                            float *pm1, float *pm25, float *pm10)
{
    if (volume_l < 0.001f) {
        *pm1 = *pm25 = *pm10 = 0.0f;
        return;
    }

    float edges[DEFAULT_BIN_COUNT + 1];
    uint8_t n;
    calibration_get_bin_edges(edges, &n);

    float pm1_sum = 0, pm25_sum = 0, pm10_sum = 0;

    for (uint8_t i = 0; i < NUM_CHANNELS; ++i) {
        /* Midpoint diameter */
        float d_mid = 0.5f * (edges[i] + edges[i + 1]);
        if (hygro) d_mid = hygroscopic_growth(d_mid, rh_pct);

        /* Number concentration (#/L) */
        num_per_l[i] = (float)counts[i] / volume_l;

        /* Mass per particle (µg):
           V = (π/6)·d³ where d in cm = d_µm / 1e4
           mass_g = ρ · V
           mass_µg = mass_g · 1e6 = ρ · (π/6) · (d/1e4)^3 · 1e6 */
        float d_cm = d_mid / 10000.0f;
        float vol_cm3 = (PI / 6.0f) * d_cm * d_cm * d_cm;
        float mass_ug = rho * vol_cm3 * 1e6f;

        float bin_mass_ugm3 = num_per_l[i] * mass_ug * 1000.0f;   /* #/L → #/m³ */

        if (d_mid <= 1.0f)  pm1_sum  += bin_mass_ugm3;
        if (d_mid <= 2.5f)  pm25_sum += bin_mass_ugm3;
        if (d_mid <= 10.0f) pm10_sum += bin_mass_ugm3;
    }

    /* PM1 ≤ PM2.5 ≤ PM10 (PM2.5 includes PM1; PM10 includes PM2.5) */
    *pm1  = pm1_sum;
    *pm25 = pm25_sum;
    *pm10 = pm10_sum;
}

const float *concentration_number_per_l(void) { return num_per_l; }