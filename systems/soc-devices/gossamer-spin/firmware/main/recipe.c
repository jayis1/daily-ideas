/*
 * gossamer-spin / firmware / recipe.c
 * 8 preset polymer electrospinning recipes.
 *
 * Each recipe defines: voltage, flow rate, drum RPM, needle-collector
 * distance, target humidity range, target temperature, and duration.
 * Values are based on typical parameters from electrospinning literature.
 */
#include "main.h"

const char *const RECIPE_NAMES[NUM_RECIPES] = {
    "PVA", "PAN", "PLLA", "PVDF",
    "Nylon-6", "Chitosan", "PS", "Custom"
};

/* Default recipe parameters (8 recipes) */
static recipe_t recipes[NUM_RECIPES];

static void init_recipes(void)
{
    /* 0: PVA (polyvinyl alcohol) — water-soluble, filtration, hydrogels */
    strcpy(recipes[0].name, "PVA");
    recipes[0].voltage_kv    = 18.0f;
    recipes[0].flow_mlh      = 1.0f;
    recipes[0].drum_rpm      = 800;
    recipes[0].distance_cm   = 15.0f;
    recipes[0].target_rh_min = 30.0f;
    recipes[0].target_rh_max = 50.0f;
    recipes[0].target_temp_c = 25.0f;
    recipes[0].duration_s    = 1800;  /* 30 min */

    /* 1: PAN (polyacrylonitrile) — carbon fiber precursor */
    strcpy(recipes[1].name, "PAN");
    recipes[1].voltage_kv    = 20.0f;
    recipes[1].flow_mlh      = 0.8f;
    recipes[1].drum_rpm      = 1200;
    recipes[1].distance_cm   = 15.0f;
    recipes[1].target_rh_min = 20.0f;
    recipes[1].target_rh_max = 40.0f;
    recipes[1].target_temp_c = 25.0f;
    recipes[1].duration_s    = 3600;  /* 60 min */

    /* 2: PLLA (poly-L-lactic acid) — biomedical scaffolds */
    strcpy(recipes[2].name, "PLLA");
    recipes[2].voltage_kv    = 15.0f;
    recipes[2].flow_mlh      = 0.5f;
    recipes[2].drum_rpm      = 600;
    recipes[2].distance_cm   = 12.0f;
    recipes[2].target_rh_min = 25.0f;
    recipes[2].target_rh_max = 45.0f;
    recipes[2].target_temp_c = 25.0f;
    recipes[2].duration_s    = 1800;

    /* 3: PVDF (polyvinylidene fluoride) — piezoelectric sensors */
    strcpy(recipes[3].name, "PVDF");
    recipes[3].voltage_kv    = 22.0f;
    recipes[3].flow_mlh      = 1.2f;
    recipes[3].drum_rpm      = 1500;
    recipes[3].distance_cm   = 15.0f;
    recipes[3].target_rh_min = 20.0f;
    recipes[3].target_rh_max = 35.0f;
    recipes[3].target_temp_c = 25.0f;
    recipes[3].duration_s    = 2400;  /* 40 min */

    /* 4: Nylon-6 — filtration, textiles */
    strcpy(recipes[4].name, "Nylon-6");
    recipes[4].voltage_kv    = 20.0f;
    recipes[4].flow_mlh      = 0.6f;
    recipes[4].drum_rpm      = 1000;
    recipes[4].distance_cm   = 15.0f;
    recipes[4].target_rh_min = 30.0f;
    recipes[4].target_rh_max = 50.0f;
    recipes[4].target_temp_c = 25.0f;
    recipes[4].duration_s    = 1800;

    /* 5: Chitosan — wound dressing, antimicrobial */
    strcpy(recipes[5].name, "Chitosan");
    recipes[5].voltage_kv    = 12.0f;
    recipes[5].flow_mlh      = 0.3f;
    recipes[5].drum_rpm      = 400;
    recipes[5].distance_cm   = 10.0f;
    recipes[5].target_rh_min = 35.0f;
    recipes[5].target_rh_max = 55.0f;
    recipes[5].target_temp_c = 25.0f;
    recipes[5].duration_s    = 1200;  /* 20 min */

    /* 6: PS (polystyrene) — scaffolds, filtration */
    strcpy(recipes[6].name, "PS");
    recipes[6].voltage_kv    = 16.0f;
    recipes[6].flow_mlh      = 0.7f;
    recipes[6].drum_rpm      = 900;
    recipes[6].distance_cm   = 12.0f;
    recipes[6].target_rh_min = 25.0f;
    recipes[6].target_rh_max = 45.0f;
    recipes[6].target_temp_c = 25.0f;
    recipes[6].duration_s    = 1800;

    /* 7: Custom — user-defined via BLE app, defaults to PVA */
    strcpy(recipes[7].name, "Custom");
    recipes[7].voltage_kv    = 18.0f;
    recipes[7].flow_mlh      = 1.0f;
    recipes[7].drum_rpm      = 800;
    recipes[7].distance_cm   = 15.0f;
    recipes[7].target_rh_min = 20.0f;
    recipes[7].target_rh_max = 60.0f;
    recipes[7].target_temp_c = 25.0f;
    recipes[7].duration_s    = 1800;
}

void recipe_init(void)
{
    init_recipes();
}

void recipe_load(int idx, recipe_t *r)
{
    if (idx < 0 || idx >= NUM_RECIPES) idx = 0;
    *r = recipes[idx];
}