/*
 * synth.c — 16-voice wavetable synth with bore resonator
 *
 * Architecture:
 *   - 8 single-cycle wavetables (256 samples each, int16 Q15)
 *   - Per-voice phase accumulator at note frequency
 *   - One-pole lowpass "bore resonator" tuned to note frequency
 *     (models the acoustic waveguide of a wind instrument bore)
 *   - ADSR envelope (breath-gated: attack on note_on, release on note_off
 *     or when breath drops)
 *   - Breath noise injection (white noise × breath × noise_mix)
 *   - Vibrato and pitch-bend applied to phase increment
 */
#include "synth.h"
#include "audio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include <math.h>
#include <string.h>

static const char *TAG = "synth";

aero_state_t g_state = {0};
synth_voice_t synth_voices[SYNTH_N_VOICES];

/* ── Wavetables (256 samples, Q15 int16) ─────────────────────────────── */
#define WT_LEN 256
static int16_t wt_sine[WT_LEN];
static int16_t wt_triangle[WT_LEN];
static int16_t wt_saw[WT_LEN];
static int16_t wt_square[WT_LEN];
static int16_t wt_formant_a[WT_LEN];
static int16_t wt_formant_b[WT_LEN];
static int16_t wt_bright[WT_LEN];
static int16_t wt_breath[WT_LEN];   /* filtered noise */

const int16_t *wavetables[N_WAVETABLES] = {
    wt_sine, wt_triangle, wt_saw, wt_square,
    wt_formant_a, wt_formant_b, wt_bright, wt_breath
};
const int WAVETABLE_LEN = WT_LEN;

/* Simple LCG PRNG for breath noise */
static uint32_t prng_state = 0x12345;
static inline float prng_uniform(void)
{
    prng_state = prng_state * 1664525u + 1013904223u;
    return ((prng_state >> 8) & 0xFFFFFF) / (float)0x1000000 - 0.5f;
}

static void build_wavetables(void)
{
    for (int i = 0; i < WT_LEN; i++) {
        float t = (float)i / WT_LEN;

        wt_sine[i] = (int16_t)(sinf(t * 2.0f * M_PI) * 32767.0f);

        wt_triangle[i] = (int16_t)(
            (t < 0.5f ? (4.0f * t - 1.0f) : (3.0f - 4.0f * t)) * 32767.0f);

        wt_saw[i] = (int16_t)((2.0f * t - 1.0f) * 32767.0f);

        wt_square[i] = (int16_t)((t < 0.5f ? 1.0f : -1.0f) * 32767.0f);

        /* Formant A: sine + 2nd harmonic emphasized (vowel "ah") */
        wt_formant_a[i] = (int16_t)((
            0.6f * sinf(t * 2 * M_PI) +
            0.3f * sinf(t * 4 * M_PI) +
            0.1f * sinf(t * 6 * M_PI)
        ) * 32767.0f);

        /* Formant B: brighter (vowel "ee") */
        wt_formant_b[i] = (int16_t)((
            0.4f * sinf(t * 2 * M_PI) +
            0.4f * sinf(t * 8 * M_PI) +
            0.2f * sinf(t * 12 * M_PI)
        ) * 32767.0f);

        /* Bright pulse: bandlimited square (3 harmonics) */
        wt_bright[i] = (int16_t)((
            sinf(t * 2 * M_PI) +
            0.33f * sinf(t * 6 * M_PI) +
            0.20f * sinf(t * 10 * M_PI)
        ) * 24000.0f);

        /* Breath noise: pre-generated filtered noise (one cycle, repeated) */
        wt_breath[i] = (int16_t)(prng_uniform() * 16384.0f);
    }
    ESP_LOGI(TAG, "Wavetables built (%d tables × %d samples)",
             N_WAVETABLES, WT_LEN);
}

void synth_init(void)
{
    build_wavetables();
    memset(synth_voices, 0, sizeof(synth_voices));
    for (int i = 0; i < SYNTH_N_VOICES; i++)
        synth_voices[i].note = -1;
}

static float note_to_freq(int8_t note, int8_t transpose, int8_t octave_base)
{
    int midi = note + transpose + octave_base * 12;
    return 440.0f * powf(2.0f, (midi - 69) / 12.0f);
}

void synth_note_on(int8_t note, uint8_t vel, const patch_t *patch)
{
    /* Find free voice (or steal oldest) */
    int v = -1;
    for (int i = 0; i < SYNTH_N_VOICES; i++) {
        if (synth_voices[i].note == -1) { v = i; break; }
    }
    if (v < 0) {
        /* Steal voice 0 (simple voice-stealing) */
        v = 0;
    }
    synth_voices[v].note = note;
    synth_voices[v].freq = note_to_freq(note, patch->transpose, patch->octave_base);
    synth_voices[v].phase = 0;
    synth_voices[v].amp = 0;
    synth_voices[v].target_amp = (float)vel / 127.0f;
    synth_voices[v].bore_filt = 0;
    synth_voices[v].wt = patch->wt_index;
    ESP_LOGD(TAG, "Note on %d vel %d → voice %d freq=%.1f",
             note, vel, v, synth_voices[v].freq);
}

void synth_note_off(int8_t note)
{
    for (int i = 0; i < SYNTH_N_VOICES; i++) {
        if (synth_voices[i].note == note) {
            synth_voices[i].target_amp = 0;  /* release */
        }
    }
}

static int16_t lookup_wt(const int16_t *wt, float phase)
{
    /* phase in [0,1) → interpolate */
    float pos = phase * WT_LEN;
    int   i0 = (int)pos;
    float frac = pos - i0;
    int   i1 = (i0 + 1) % WT_LEN;
    return (int16_t)(wt[i0] * (1.0f - frac) + wt[i1] * frac);
}

static float bore_filter(float input, float *state, float freq)
{
    /* One-pole lowpass tuned to note frequency.
     * Cutoff ≈ freq × 3 (models bore resonance at the fundamental).
     * alpha = 1 - exp(-2π × cutoff / SR */
    float cutoff = freq * 3.0f;
    float alpha = 1.0f - expf(-2.0f * M_PI * cutoff / SYNTH_SR);
    float out = *state + alpha * (input - *state);
    *state = out;
    return out;
}

static int16_t bend_cents_accum = 0;
static uint8_t mod_cc1 = 0;
static float vib_rate = 0, vib_depth = 0;

void synth_set_bend_cents(int16_t cents) { bend_cents_accum = cents; }
void synth_set_modulation(uint8_t cc1) { mod_cc1 = cc1; }
void synth_set_vibrato(float r, float d) { vib_rate = r; vib_depth = d; }

/* Breath amplitude (0..1), applied to all voices */
static float breath_amp = 0;

void synth_set_breath(float v01, const patch_t *patch)
{
    /* Apply per-patch breath curve */
    float exp = patch->breath_curve_exp / 4.0f;
    breath_amp = powf(v01, exp);
}

void synth_render_block(int16_t *stereo, int n_frames)
{
    const patch_t *patch = &g_state.patch;

    for (int f = 0; f < n_frames; f++) {
        float L = 0, R = 0;

        /* Vibrato LFO */
        float vib_phase = (float)(esp_timer_get_time() / 1000) * vib_rate * 2.0f * M_PI / 1000.0f;
        float vib_cents = sinf(vib_phase) * vib_depth;

        for (int v = 0; v < SYNTH_N_VOICES; v++) {
            synth_voice_t *vc = &synth_voices[v];
            if (vc->note < 0) continue;

            /* Envelope: attack/decay/sustain/release (simplified) */
            float atk = patch->attack / 127.0f * 0.01f + 0.001f;
            float rel = patch->release / 127.0f * 0.5f + 0.01f;
            if (vc->target_amp > vc->amp) {
                vc->amp += (1.0f / SYNTH_SR) / atk;
                if (vc->amp > vc->target_amp) vc->amp = vc->target_amp;
            } else {
                vc->amp -= (1.0f / SYNTH_SR) / rel;
                if (vc->amp <= 0.0f) {
                    vc->amp = 0;
                    vc->note = -1;
                    continue;
                }
            }

            /* Phase increment with bend + vibrato */
            float bend_ratio = powf(2.0f, (bend_cents_accum + vib_cents) / 1200.0f);
            float freq = vc->freq * bend_ratio;
            float inc = freq / SYNTH_SR;
            vc->phase += inc;
            if (vc->phase >= 1.0f) vc->phase -= 1.0f;

            /* Wavetable lookup */
            const int16_t *wt = wavetables[vc->wt % N_WAVETABLES];
            int16_t sample = lookup_wt(wt, vc->phase);

            /* Bore resonator filter */
            float s = bore_filter((float)sample, &vc->bore_filt, freq);

            /* Breath noise injection */
            float noise = prng_uniform() * breath_amp * (patch->noise_mix / 127.0f) * 0.3f;

            /* Apply amplitude × breath × voice env */
            float out = (s / 32768.0f + noise) * vc->amp * breath_amp;

            /* Stereo: slight pan per voice */
            float pan = (v % SYNTH_N_VOICES) / (float)SYNTH_N_VOICES - 0.5f;
            L += out * (0.5f - pan * 0.3f);
            R += out * (0.5f + pan * 0.3f);
        }

        /* Clip and scale to int16 */
        if (L > 1.0f) L = 1.0f;
        if (L < -1.0f) L = -1.0f;
        if (R > 1.0f) R = 1.0f;
        if (R < -1.0f) R = -1.0f;

        stereo[f * 2 + 0] = (int16_t)(L * 32767.0f);
        stereo[f * 2 + 1] = (int16_t)(R * 32767.0f);
    }
}

void synth_task(void *arg)
{
    (void)arg;
    const int BLOCK = 128;  /* 128 frames × 2 channels × 2 bytes = 512 bytes */
    int16_t buf[BLOCK * 2];
    TickType_t last = xTaskGetTickCount();

    while (1) {
        synth_render_block(buf, BLOCK);
        audio_write_block(buf, BLOCK * 2 * sizeof(int16_t));

        /* Maintain ~44100 Hz pace */
        vTaskDelayUntil(&last, pdMS_TO_TICKS(BLOCK * 1000 / SYNTH_SR));
    }
}