/*
 * touch.c — capacitive touch fingering (ESP32-S3 touch peripheral)
 *
 * Implements a saxophone-style fingering system on 14 touch pads.
 * The fingering table maps pad-combinations to MIDI note numbers.
 * Octave shift is controlled by the two thumb pads.
 */
#include "touch.h"
#include "driver/touch_pad.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "touch";

/* GPIO → touch channel mapping (ESP32-S3 T1..T14 = GPIO1..GPIO14) */
static const int pad_gpio[N_PADS] = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
};

/* Calibrated thresholds — each pad has a separate press threshold */
static uint32_t pad_thresh[N_PADS] = {0};
static uint32_t pad_baseline[N_PADS] = {0};
static bool     pad_held[N_PADS] = {0};

/* ── Saxophone-style fingering table ──────────────────────────────────
 * Each entry: 13-bit pad mask (excluding octave pads) → note offset from C.
 * We use a simplified Boehm-system sax fingering.
 * pad bits: L1..L5, R1..R5, BEND, ALT  (12 bits, bits 1..12 of the mask)
 */
typedef struct {
    uint32_t mask;   /* expected held pads (non-octave) */
    int8_t   offset; /* semitone offset from C (60) */
} fingering_t;

static const fingering_t fingering_table[] = {
    /* All open → C */
    { 0x0000, 0 },
    /* R5 closed → B */
    { (1<<PAD_RH5), -1 },
    /* R5+R4 → Bb */
    { (1<<PAD_RH5)|(1<<PAD_RH4), -2 },
    /* R5+R4+R3 → A */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3), -3 },
    /* R5+R4+R3+R2 → Ab */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2), -4 },
    /* R5+R4+R3+R2+R1 → G */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1), -5 },
    /* G + L5 → Gb */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5), -6 },
    /* G + L5 + L4 → F */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4), -7 },
    /* F + L3 → E */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4)|(1<<PAD_LH3), -8 },
    /* E + L2 → Eb */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4)|(1<<PAD_LH3)|(1<<PAD_LH2), -9 },
    /* E + L1 → D */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4)|(1<<PAD_LH3)|(1<<PAD_LH1), -10 },
    /* D + L2 + L1 → Db */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4)|(1<<PAD_LH3)|(1<<PAD_LH2)|(1<<PAD_LH1), -11 },
    /* All closed → C (low) */
    { (1<<PAD_RH5)|(1<<PAD_RH4)|(1<<PAD_RH3)|(1<<PAD_RH2)|(1<<PAD_RH1)|(1<<PAD_LH5)|(1<<PAD_LH4)|(1<<PAD_LH3)|(1<<PAD_LH2)|(1<<PAD_LH1), -12 },
    /* ALT pad held → +1 semitone (trill/alt) */
    { (1<<PAD_ALT), 1 },
};

#define N_FINGERINGS (sizeof(fingering_table)/sizeof(fingering_table[0]))

void touch_init(void)
{
    /* Initialize touch peripheral */
    touch_pad_init();
    touch_pad_set_voltage(TOUCH_HVOLT_2V7, TOUCH_LVOLT_0V5,
                           TOUCH_HVOLT_ATTEN_1V);
    touch_pad_set_meas_time(0x7fff);

    for (int i = 0; i < N_PADS; i++) {
        touch_pad_config((touch_pad_t)i);
        /* Read initial baseline */
        uint32_t val = 0;
        touch_pad_read_raw((touch_pad_t)i, &val);
        pad_baseline[i] = val;
        pad_thresh[i] = val * 3 / 4;  /* press when signal drops 25% */
    }
    ESP_LOGI(TAG, "Touch initialised, %d pads", N_PADS);
}

void touch_scan(void)
{
    for (int i = 0; i < N_PADS; i++) {
        uint32_t val = 0;
        esp_err_t r = touch_pad_read_raw((touch_pad_t)i, &val);
        if (r != ESP_OK) continue;

        /* Track slow baseline drift */
        pad_baseline[i] = (pad_baseline[i] * 15 + val) / 16;

        /* A pad is "held" when the reading drops below threshold
         * (touch increases capacitance → lower reading on ESP32-S3) */
        if (val < pad_thresh[i] && (pad_baseline[i] - val) > (pad_baseline[i] / 8)) {
            pad_held[i] = true;
        } else {
            pad_held[i] = false;
        }
    }
}

bool touch_pad_held(pad_id_t p)
{
    if (p >= N_PADS) return false;
    return pad_held[p];
}

uint32_t touch_pad_mask(void)
{
    uint32_t m = 0;
    for (int i = 0; i < N_PADS; i++) {
        if (pad_held[i]) m |= (1U << i);
    }
    return m;
}

int8_t touch_octave_offset(void)
{
    if (pad_held[PAD_OCT_UP])   return 1;
    if (pad_held[PAD_OCT_DOWN]) return -1;
    return 0;
}

int16_t touch_decode_note(void)
{
    uint32_t mask = touch_pad_mask();
    /* strip octave pads from the matching mask */
    uint32_t fmask = mask & ~((1U<<PAD_OCT_UP) | (1U<<PAD_OCT_DOWN));

    int8_t best_offset = 0;
    bool found = false;

    /* Find the fingering whose mask matches the held pads.
     * We look for exact match of the non-octave pad set. */
    for (int i = 0; i < (int)N_FINGERINGS; i++) {
        if (fmask == fingering_table[i].mask) {
            best_offset = fingering_table[i].offset;
            found = true;
            break;
        }
    }
    if (!found) return -1;

    /* Base note: C4 = 60, apply octave offset and transpose */
    int16_t note = 60 + best_offset;
    note += touch_octave_offset() * 12;

    /* Clamp to valid MIDI range */
    if (note < 0) note = 0;
    if (note > 127) note = 127;
    return note;
}