/*
 * gossamer-spin / firmware / safety.c
 * Triple-redundant HV safety: door interlock + tilt sensor + comparator + IWDG.
 *
 * The three hardware cutoffs (door reed, tilt, TLV3201 comparator) are
 * diode-ORed into a single HV_CUTOFF line that physically disables the
 * boost converter MOSFET gate driver, regardless of firmware state.
 * The firmware reads the individual sources for status reporting.
 */
#include "main.h"

static struct {
    uint8_t source;     /* which safety source tripped */
    bool    tripped;
} saf = { SAF_NONE, false };

static void *h_iwdg = (void *)1;

/* Read the hardware cutoff line (PA11). If low, something tripped. */
static bool read_hv_cutoff(void)
{
    /* In real build: return gpio_read(PA11) == 0; (active low)
       Placeholder: always safe. */
    return true;  /* true = no cutoff */
}

/* Read individual safety sensors to determine which one tripped */
static uint8_t read_safety_source(void)
{
    /* In real build:
       - Read PA12 (DOOR_INT): reed switch, low = door open
       - Read PA13 (TILT): ball sensor, low = tipped
       - Read comparator output (separate pin or via ADC): high = over-current

       Placeholder: return SAF_NONE. */
    return SAF_NONE;
}

void safety_init(void)
{
    saf.source = SAF_NONE;
    saf.tripped = false;

    /* Configure GPIOs:
       - PA11 (HV_CUTOFF): input, pull-up, falling-edge interrupt
       - PA12 (DOOR_INT): input, pull-up
       - PA13 (TILT): input, pull-up
       - Enable IWDG with 2-second timeout */

    /* IWDG init: prescaler /256, reload 1250 → ~2 s at LSI 32 kHz
       (256 / 32000) × 1250 = 10 s... adjust: prescaler /32, reload 2000
       (32/32000) × 2000 = 2 s */
    (void)h_iwdg;
}

bool safety_check(void)
{
    if (!read_hv_cutoff()) {
        saf.tripped = true;
        saf.source = read_safety_source();
        if (saf.source == SAF_NONE) {
            /* Cutoff active but individual sensors read OK → comparator */
            saf.source = SAF_CURRENT;
        }
        return false;
    }

    /* Check individual sensors (even if hardware cutoff not triggered,
       we want early warning) */
    uint8_t src = read_safety_source();
    if (src != SAF_NONE) {
        saf.tripped = true;
        saf.source = src;
        return false;
    }

    /* Refresh IWDG */
    /* HAL_IWDG_Refresh(h_iwdg); */

    return true;
}

uint8_t safety_get_source(void)
{
    return saf.source;
}

void safety_reset(void)
{
    /* Only reset if all sensors are clear */
    if (read_hv_cutoff() && read_safety_source() == SAF_NONE) {
        saf.tripped = false;
        saf.source = SAF_NONE;
    }
}