/*
 * patch.c — patch storage in NVS (8 patches, 32 bytes each)
 */
#include "patch.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "patch";
#define N_PATCHES 8
#define NVS_NAMESPACE "aero_reed"

static patch_t patches[N_PATCHES] = {0};

/* Default patches */
static const patch_t default_patches[N_PATCHES] = {
    /* 0: Soprano Sax */
    { .wt_index = WT_SAW, .transpose = 0, .breath_curve_exp = 6,
      .breath_cc_exp = 4, .bore_q_x10 = 8, .noise_mix = 30,
      .bend_range_semi = 2, .growl_depth = 20, .tilt_mod = 60,
      .vibrato_rate_x2 = 12, .vibrato_depth_cents = 30,
      .attack = 5, .decay = 20, .sustain = 90, .release = 40,
      .octave_base = 0, .name = "Soprano Sax" },
    /* 1: Flute */
    { .wt_index = WT_SINE, .transpose = 0, .breath_curve_exp = 4,
      .breath_cc_exp = 4, .bore_q_x10 = 15, .noise_mix = 50,
      .bend_range_semi = 2, .growl_depth = 0, .tilt_mod = 80,
      .vibrato_rate_x2 = 14, .vibrato_depth_cents = 25,
      .attack = 8, .decay = 10, .sustain = 95, .release = 30,
      .octave_base = 0, .name = "Flute" },
    /* 2: Clarinet */
    { .wt_index = WT_TRIANGLE, .transpose = 0, .breath_curve_exp = 5,
      .breath_cc_exp = 4, .bore_q_x10 = 12, .noise_mix = 25,
      .bend_range_semi = 1, .growl_depth = 10, .tilt_mod = 40,
      .vibrato_rate_x2 = 10, .vibrato_depth_cents = 15,
      .attack = 3, .decay = 15, .sustain = 88, .release = 50,
      .octave_base = -1, .name = "Clarinet" },
    /* 3: Synth Lead */
    { .wt_index = WT_SAW, .transpose = 0, .breath_curve_exp = 3,
      .breath_cc_exp = 3, .bore_q_x10 = 4, .noise_mix = 10,
      .bend_range_semi = 5, .growl_depth = 40, .tilt_mod = 100,
      .vibrato_rate_x2 = 16, .vibrato_depth_cents = 50,
      .attack = 2, .decay = 20, .sustain = 85, .release = 60,
      .octave_base = 0, .name = "Synth Lead" },
    /* 4: Warm Pad */
    { .wt_index = WT_FORMANT_A, .transpose = 0, .breath_curve_exp = 4,
      .breath_cc_exp = 4, .bore_q_x10 = 6, .noise_mix = 5,
      .bend_range_semi = 2, .growl_depth = 0, .tilt_mod = 127,
      .vibrato_rate_x2 = 8, .vibrato_depth_cents = 20,
      .attack = 40, .decay = 40, .sustain = 80, .release = 80,
      .octave_base = 0, .name = "Warm Pad" },
    /* 5: Reed Growl */
    { .wt_index = WT_SQUARE, .transpose = 0, .breath_curve_exp = 7,
      .breath_cc_exp = 5, .bore_q_x10 = 10, .noise_mix = 40,
      .bend_range_semi = 2, .growl_depth = 80, .tilt_mod = 50,
      .vibrato_rate_x2 = 18, .vibrato_depth_cents = 40,
      .attack = 10, .decay = 30, .sustain = 90, .release = 45,
      .octave_base = 0, .name = "Reed Growl" },
    /* 6: Bright Pulse */
    { .wt_index = WT_BRIGHT_PULSE, .transpose = 0, .breath_curve_exp = 4,
      .breath_cc_exp = 4, .bore_q_x10 = 7, .noise_mix = 15,
      .bend_range_semi = 4, .growl_depth = 30, .tilt_mod = 80,
      .vibrato_rate_x2 = 12, .vibrato_depth_cents = 35,
      .attack = 4, .decay = 25, .sustain = 85, .release = 50,
      .octave_base = 0, .name = "Bright Pulse" },
    /* 7: Breath Noise */
    { .wt_index = WT_BREATH_NOISE, .transpose = 0, .breath_curve_exp = 2,
      .breath_cc_exp = 3, .bore_q_x10 = 20, .noise_mix = 100,
      .bend_range_semi = 1, .growl_depth = 0, .tilt_mod = 30,
      .vibrato_rate_x2 = 6, .vibrato_depth_cents = 10,
      .attack = 20, .decay = 10, .sustain = 70, .release = 100,
      .octave_base = 0, .name = "Breath Noise" },
};

void patch_load_all(void)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h) != ESP_OK) {
        ESP_LOGW(TAG, "NVS open failed; using defaults");
        memcpy(patches, default_patches, sizeof(patches));
        return;
    }
    char key[8];
    for (int i = 0; i < N_PATCHES; i++) {
        snprintf(key, sizeof(key), "p%d", i);
        size_t needed = sizeof(patch_t);
        if (nvs_get_blob(h, key, &patches[i], &needed) != ESP_OK) {
            /* Not found → store default */
            patches[i] = default_patches[i];
            nvs_set_blob(h, key, &patches[i], sizeof(patch_t));
        }
    }
    nvs_commit(h);
    nvs_close(h);
    ESP_LOGI(TAG, "Loaded %d patches", N_PATCHES);
}

void patch_save(int idx, const patch_t *p)
{
    if (idx < 0 || idx >= N_PATCHES) return;
    patches[idx] = *p;
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h) == ESP_OK) {
        char key[8]; snprintf(key, sizeof(key), "p%d", idx);
        nvs_set_blob(h, key, p, sizeof(patch_t));
        nvs_commit(h);
        nvs_close(h);
    }
}

patch_t *patch_get(int idx)
{
    if (idx < 0 || idx >= N_PATCHES) return &patches[0];
    return &patches[idx];
}

const char *patch_name(int idx)
{
    if (idx < 0 || idx >= N_PATCHES) return "?";
    return patches[idx].name;
}

void patch_select(int idx)
{
    if (idx < 0 || idx >= N_PATCHES) return;
}

void patch_next(void)
{
    g_state.patch_idx = (g_state.patch_idx + 1) % N_PATCHES;
    g_state.patch = *patch_get(g_state.patch_idx);
}

void patch_prev(void)
{
    g_state.patch_idx = (g_state.patch_idx - 1 + N_PATCHES) % N_PATCHES;
    g_state.patch = *patch_get(g_state.patch_idx);
}

int patch_count(void) { return N_PATCHES; }