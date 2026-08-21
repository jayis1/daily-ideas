/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * materials.c — Material longitudinal-wave velocity database
 *
 * 60+ built-in materials with their longitudinal and shear wave velocities
 * and densities. Custom materials (slots ≥ BUILTIN) are user-editable and
 * persisted to flash.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "materials.h"
#include <string.h>

#define MATERIAL_COUNT_BUILTIN  64
#define MATERIAL_FLASH_OFFSET    0x08060000U   /* last 16 KB sector of flash */

static material_t g_materials[MAX_MATERIALS];
static uint8_t    g_default_idx = 0;
static uint8_t    g_custom_count = 0;

/* ---- Built-in material table ---- */
static const material_t k_builtin[MATERIAL_COUNT_BUILTIN] = {
    {"Steel (mild)",        5920, 3220, 7.85f},
    {"Steel (stainless 304)", 5660, 3120, 8.00f},
    {"Steel (stainless 316)", 5740, 3120, 8.00f},
    {"Steel (carbon 1020)",  5890, 3220, 7.87f},
    {"Steel (tool, hardened)", 5900, 3220, 7.85f},
    {"Steel (cast)",         4600, 2320, 7.70f},
    {"Aluminum (6061)",      6320, 3130, 2.70f},
    {"Aluminum (2024)",      6370, 3130, 2.78f},
    {"Aluminum (7075)",      6300, 3130, 2.81f},
    {"Aluminum (cast A356)", 6710, 3380, 2.68f},
    {"Copper",               4760, 2320, 8.96f},
    {"Brass (naval)",         4430, 2120, 8.40f},
    {"Bronze (phosphor)",     4400, 2200, 8.80f},
    {"Titanium (grade 5)",    6100, 3120, 4.43f},
    {"Titanium (grade 2)",    6070, 3120, 4.51f},
    {"Nickel",                5480, 2990, 8.90f},
    {"Monel 400",             5350, 2720, 8.80f},
    {"Inconel 625",           5820, 3120, 8.44f},
    {"Tungsten",              5180, 2870, 19.3f},
    {"Zinc",                  4170, 2410, 7.13f},
    {"Lead",                  2160, 760,  11.34f},
    {"Tin",                   3320, 1670, 7.27f},
    {"Silver",                3650, 1760, 10.5f},
    {"Gold",                  3240, 1190, 19.3f},
    {"Magnesium (AZ31B)",     5770, 3050, 1.77f},
    {"Beryllium copper",      4700, 2380, 8.25f},
    {"Zirconium",             4650, 2320, 6.50f},
    {"Cast iron (grey)",      4600, 2320, 7.20f},
    {"Cast iron (ductile)",   5600, 3120, 7.10f},
    {"Ductile iron",          5600, 3120, 7.10f},
    {"Glass (soda-lime)",     5640, 3280, 2.50f},
    {"Glass (borosilicate)",  5640, 3280, 2.23f},
    {"Glass (fused silica)",  5970, 3760, 2.20f},
    {"Acrylic (PMMA)",        2730, 1340, 1.18f},
    {"Polycarbonate",         2300, 950,  1.20f},
    {"Nylon 6/6",             2620, 1080, 1.14f},
    {"PVC",                   2390, 1130, 1.40f},
    {"PTFE (Teflon)",         1350, 510,  2.20f},
    {"HDPE",                  2430, 950,  0.95f},
    {"ABS",                   2240, 1000, 1.05f},
    {"Delrin (POM)",          2440, 1030, 1.42f},
    {"Carbon fiber laminate", 3200, 1700, 1.55f},
    {"Glass fiber laminate",  2750, 1450, 1.90f},
    {"Concrete",              4250, 2400, 2.40f},
    {"Granite",               5950, 3290, 2.70f},
    {"Marble",                6150, 3360, 2.70f},
    {"Ceramic (alumina)",    10000, 5800, 3.90f},
    {"Ceramic (zirconia)",    7000, 4000, 6.00f},
    {"Silicon",               8430, 5840, 2.33f},
    {"Water (20C)",           1480, 0,    1.00f},
    {"Ice",                   3980, 1900, 0.92f},
    {"Wood (oak, //grain)",    3940, 1500, 0.77f},
    {"Wood (pine, //grain)",   5070, 1800, 0.50f},
    {"Rubber (neoprene)",      1600, 780,  1.23f},
    {"Rubber (silicone)",      980,  420,  1.20f},
    {"Epoxy resin",            2650, 1150, 1.20f},
    {"Aluminum oxide",         9900, 5800, 3.97f},
    {"Invar 36",              4590, 2400, 8.05f},
    {"Hastelloy C276",        5840, 3170, 8.89f},
    {"Stellite",               4500, 2300, 8.50f},
    {"Tungsten carbide",       6650, 3780, 15.6f},
    {"Beryllium",              12890, 8900, 1.85f},
    {"Uranium",                3370, 1940, 19.1f},
    {"Diamond",               17500, 12800, 3.52f},
};

void materials_init(void)
{
    memset(g_materials, 0, sizeof(g_materials));
    /* Copy built-in table */
    for (uint8_t i = 0; i < MATERIAL_COUNT_BUILTIN && i < MAX_MATERIALS; i++)
        g_materials[i] = k_builtin[i];
    g_custom_count = 0;
    g_default_idx = 0;
}

uint8_t materials_count(void)
{
    return MATERIAL_COUNT_BUILTIN + g_custom_count;
}

const material_t *materials_get(uint8_t idx)
{
    if (idx >= materials_count()) return NULL;
    return &g_materials[idx];
}

int8_t materials_find_by_name(const char *name)
{
    if (!name) return -1;
    for (uint8_t i = 0; i < materials_count(); i++) {
        if (strncmp(g_materials[i].name, name, MATERIAL_NAME_MAX) == 0)
            return (int8_t)i;
    }
    return -1;
}

uint8_t materials_set_default(uint8_t idx)
{
    if (idx >= materials_count()) return 0;
    g_default_idx = idx;
    return 1;
}

uint8_t materials_get_default_idx(void) { return g_default_idx; }

uint8_t materials_add_custom(const char *name, uint32_t vel_mps,
                                uint32_t shear_mps, float density)
{
    uint8_t slot = MATERIAL_COUNT_BUILTIN + g_custom_count;
    if (slot >= MAX_MATERIALS) return 0;
    if (vel_mps < VELOCITY_MIN_MPS || vel_mps > VELOCITY_MAX_MPS) return 0;
    material_t *m = &g_materials[slot];
    memset(m, 0, sizeof(*m));
    for (uint8_t i = 0; i < MATERIAL_NAME_MAX - 1 && name[i]; i++)
        m->name[i] = name[i];
    m->velocity_mps      = vel_mps;
    m->shear_velocity_mps = shear_mps;
    m->density_gcc        = density;
    g_custom_count++;
    return 1;
}

/* ---- Flash persistence ---- */
/* STM32G474: flash is 2 KB page size. We store the custom materials + default
 * index in a dedicated page. Simplified: erase + write via the flash controller. */
void materials_save_to_flash(void)
{
    /* Unlock flash */
    FLASH->KEYR = 0x45670123U;
    FLASH->KEYR = 0xCDEF89ABU;

    /* Erase the page at MATERIAL_FLASH_OFFSET */
    FLASH->CR |= FLASH_CR_PER;
    FLASH->AR = MATERIAL_FLASH_OFFSET;
    FLASH->CR |= FLASH_CR_STTR;
    while (FLASH->SR & FLASH_CR_STRT) { }   /* wait */
    FLASH->CR &= ~FLASH_CR_PER;

    /* Program custom materials as 16-bit half-words */
    FLASH->CR |= FLASH_CR_PG;
    uint16_t *dst = (uint16_t *)MATERIAL_FLASH_OFFSET;
    uint16_t *src = (uint16_t *)&g_materials[MATERIAL_COUNT_BUILTIN];
    uint16_t words = (MAX_MATERIALS - MATERIAL_COUNT_BUILTIN) *
                     sizeof(material_t) / 2;
    for (uint16_t i = 0; i < words; i++) {
        dst[i] = src[i];
        while (FLASH->SR & FLASH_SR_BSY) { }
    }
    /* Also store default index + custom count */
    dst[words]     = g_default_idx;
    dst[words + 1] = g_custom_count;
    while (FLASH->SR & FLASH_SR_BSY) { }
    FLASH->CR &= ~FLASH_CR_PG;
    FLASH->CR |= FLASH_CR_LOCK;
}

void materials_load_from_flash(void)
{
    uint16_t *src = (uint16_t *)MATERIAL_FLASH_OFFSET;
    /* Check if flash is programmed (not 0xFFFF) */
    if (src[0] == 0xFFFF) return;   /* empty flash — keep defaults */

    uint16_t *dst = (uint16_t *)&g_materials[MATERIAL_COUNT_BUILTIN];
    uint16_t words = (MAX_MATERIALS - MATERIAL_COUNT_BUILTIN) *
                     sizeof(material_t) / 2;
    for (uint16_t i = 0; i < words; i++)
        dst[i] = src[i];
    g_default_idx  = src[words] & 0xFF;
    g_custom_count = src[words + 1] & 0xFF;
    if (g_default_idx >= materials_count()) g_default_idx = 0;
}