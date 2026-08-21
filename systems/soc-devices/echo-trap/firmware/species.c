/*
 * species.c — Species class definitions, names, target/beneficial flags
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "species.h"
#include "esp_log.h"

static const char *TAG = "species";

typedef struct {
    const char *name;
    int         is_target;     /* 1 = agricultural pest / disease vector */
    int         is_beneficial; /* 1 = pollinator or predator (protect) */
    float       wb_typical_hz; /* typical wingbeat frequency */
} species_info_t;

static const species_info_t s_species[SPECIES_COUNT] = {
    { "Aedes mosquito",      1, 0, 550.0f },
    { "Culex mosquito",      1, 0, 450.0f },
    { "Anopheles mosquito", 1, 0, 400.0f },
    { "Honeybee",             0, 1, 230.0f },
    { "Drosophila (SWD)",    1, 0, 200.0f },
    { "Codling moth",         1, 0, 60.0f },
    { "Armyworm moth",       1, 0, 50.0f },
    { "Housefly",             0, 0, 180.0f },
    { "Wasp/hornet",         1, 0, 130.0f },
    { "Lacewing",             0, 1, 50.0f },
    { "Hoverfly",             0, 1, 150.0f },
    { "Unknown",              0, 0, 0.0f },
};

void species_init(void)
{
    ESP_LOGI(TAG, "Species table loaded (%d classes)", SPECIES_COUNT);
}

const char *species_name(uint8_t id)
{
    if (id >= SPECIES_COUNT) return "INVALID";
    return s_species[id].name;
}

int species_is_target(uint8_t id)
{
    if (id >= SPECIES_COUNT) return 0;
    return s_species[id].is_target;
}

int species_is_beneficial(uint8_t id)
{
    if (id >= SPECIES_COUNT) return 0;
    return s_species[id].is_beneficial;
}

float species_wingbeat_typical(uint8_t id)
{
    if (id >= SPECIES_COUNT) return 0.0f;
    return s_species[id].wb_typical_hz;
}