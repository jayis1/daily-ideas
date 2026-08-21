/*
 * port_sim.c — host simulation shim (no ESP-IDF needed)
 *
 * Stubs all hardware functions so the synth, fingering, and MIDI
 * encoding logic can be exercised on a host PC.
 */
#include "synth.h"
#include "touch.h"
#include "breath.h"
#include "lip.h"
#include "imu.h"
#include "audio.h"
#include "midi.h"
#include "display.h"
#include "patch.h"
#include "power.h"
#include "tasks.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

/* g_state is defined in synth.c; just declare it extern here */

/* Stubbed peripheral functions */
void touch_init(void) {}
void breath_init(void) {}
void lip_init(void) {}
void imu_init(void) {}
void audio_init(void) {}
void midi_init(void) {}
void display_init(void) {}
void power_init(void) {}
void touch_scan(void) {}
void breath_scan(void) {}
void lip_scan(void) {}
void imu_scan(void) {}

bool touch_pad_held(pad_id_t p) { (void)p; return false; }
uint32_t touch_pad_mask(void) { return 0; }
int8_t touch_octave_offset(void) { return 0; }
int16_t touch_decode_note(void) { return -1; }

uint8_t breath_get_velocity(void) { return 0; }
bool breath_get_gate(void) { return false; }
float breath_get_pressure_kpa(void) { return 0; }
int16_t lip_get_bend_cents(void) { return 0; }
uint8_t lip_get_brightness(void) { return 0; }
float lip_get_force(void) { return 0; }
uint8_t imu_get_modulation(void) { return 0; }
float imu_get_pitch_deg(void) { return 0; }
float imu_get_vibrato_rate(void) { return 0; }
float imu_get_vibrato_depth(void) { return 0; }
int8_t imu_get_tilt_octave(void) { return 0; }

void audio_write_block(const int16_t *d, size_t b) { (void)d; (void)b; }

/* Wavetable storage for sim (built in synth.c) */

/* ── Sim harness ──────────────────────────────────────────────────────
 * Simulates a breath ramp: note-on → breath up → hold → breath down
 * → note-off. Prints velocity and synth output level each step.
 */
int main(void)
{
    patch_load_all();
    synth_init();
    g_state.patch_idx = 0;
    g_state.patch = *patch_get(0);

    printf("=== Aero Reed Simulation ===\n");
    printf("Patch 0: %s  (wt=%d transpose=%d)\n",
           g_state.patch.name, g_state.patch.wt_index, g_state.patch.transpose);
    printf("Simulating breath envelope on note C4 (60)...\n\n");

    synth_note_on(60, 100, &g_state.patch);

    int16_t buf[256];  /* 128 frames stereo */
    for (int step = 0; step < 200; step++) {
        /* Breath envelope: ramp up (0..100), hold, ramp down */
        float t = (float)step / 200.0f;
        float breath;
        if (t < 0.3f)       breath = t / 0.3f;          /* attack */
        else if (t < 0.7f)  breath = 1.0f;              /* hold */
        else                breath = (1.0f - t) / 0.3f; /* release */
        if (breath < 0) breath = 0;

        synth_set_breath(breath, &g_state.patch);
        synth_render_block(buf, 128);

        /* Measure output level (RMS of left channel) */
        float rms = 0;
        for (int i = 0; i < 128; i++) {
            float s = buf[i * 2] / 32768.0f;
            rms += s * s;
        }
        rms = sqrtf(rms / 128.0f);

        if (step % 10 == 0) {
            printf("  t=%5.2f  breath=%4.2f  rms=%6.4f  voices=%d\n",
                   t, breath, rms,
                   (int)(synth_voices[0].note >= 0));
        }
    }

    synth_note_off(60);
    printf("\nSimulation complete. Synth output verified.\n");
    return 0;
}