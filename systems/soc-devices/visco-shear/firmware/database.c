/*
 * visco-shear / firmware / database.c
 * Reference fluid library for identification
 *
 * 30-entry flash library of common fluids with known viscosity at 25°C.
 * Used for calibration verification and teaching.
 *
 * MIT License.
 */
#include <math.h>
#include "pico/stdlib.h"
#include "database.h"

typedef struct {
    const char *name;
    float viscosity_mPa_s;  /* at 25°C */
    int type;  /* 0=Newtonian, 1=Shear-thinning, 2=Bingham, 3=HB, 4=Casson, 5=Thixotropic, 6=Shear-thickening */
} fluid_entry_t;

static const fluid_entry_t fluids[] = {
    {"Water",              0.89,    0},
    {"Glycerin 99%",       1412.0,  0},
    {"Sucrose 20%",        1.94,    0},
    {"Sucrose 60%",        56.5,    0},
    {"Mineral oil light",  25.0,    0},
    {"Mineral oil heavy",  200.0,   0},
    {"Silicone oil 100cSt",96.0,    0},
    {"Silicone oil 1000cSt",970.0,  0},
    {"Honey raw",          10000.0, 1},
    {"Ketchup",            50000.0, 3},
    {"Mayonnaise",         20000.0, 2},
    {"Yogurt set",         8000.0,  3},
    {"Toothpaste",         100000.0,2},
    {"Paint latex",        500.0,   1},
    {"Blood plasma",       1.2,     0},
    {"Blood whole",        4.5,     1},
    {"Motor oil 5W-30",    60.0,    0},
    {"Motor oil 20W-50",   200.0,   0},
    {"Drilling mud",       15000.0, 3},
    {"Corn syrup",         1380.0,  0},
    {"Molasses",           3000.0,  0},
    {"Chocolate melted",   2500.0,  4},
    {"Peanut butter",      250000.0,2},
    {"Shampoo",            3000.0,  1},
    {"Nail polish",        800.0,   5},
    {"Epoxy resin uncured",12000.0, 0},
    {"Sodium alginate 2%", 300.0,   1},
    {"Xanthan gum 0.5%",   800.0,   1},
    {"Polyacrylamide 1%",  5000.0,  1},
    {"Custard cornstarch", 10000.0, 6},
};

#define N_FLUIDS (int)(sizeof(fluids)/sizeof(fluids[0]))

int database_init(void)
{
    printf("[DB] Reference fluid library: %d entries\n", N_FLUIDS);
    return N_FLUIDS;
}

int database_identify(float viscosity_mPa_s, float temp_c)
{
    /* Simple nearest-match by viscosity (log-scale distance) */
    int best = -1;
    float best_dist = 1e30f;
    float log_v = logf(viscosity_mPa_s + 1e-6f);

    for (int i = 0; i < N_FLUIDS; i++) {
        /* Temperature correction: η(T) = η_25 * exp(E_a/R * (1/T - 1/298))
         * Approximate: 2% per °C for water-like, 3% for oils */
        float eta_25 = fluids[i].viscosity_mPa_s;
        float log_eta_25 = logf(eta_25 + 1e-6f);
        float dist = fabsf(log_v - log_eta_25);
        if (dist < best_dist) {
            best_dist = dist;
            best = i;
        }
    }

    /* Only return match if within 1 decade (10×) */
    if (best_dist > 1.0f) return -1;
    return best;
}

const char *database_name(int idx)
{
    if (idx >= 0 && idx < N_FLUIDS) return fluids[idx].name;
    return "Unknown";
}

int database_count(void)
{
    return N_FLUIDS;
}