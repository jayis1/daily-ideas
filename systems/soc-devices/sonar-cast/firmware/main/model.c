/*
 * sonar-cast / firmware / model.c
 * Shared echo-envelope feature extraction stubs + helpers.
 */
#include "main.h"

float clampf(float v, float lo, float hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

void model_init(void)
{
    /* No ML model weights needed — the detector uses physics-based
       CFAR + envelope statistics + nearest-centroid bottom class.
       This file is reserved for a future int8 CNN fish-species
       classifier (e.g. 6-class: game/rough/bait/none/clutter/bottom). */
}

/* Simple running-average smoothing for envelope display. */
void model_smooth(float *env, uint32_t n, uint8_t k)
{
    if (k == 0 || n < (uint32_t)(2 * k + 1)) return;
    static float tmp[4096];
    if (n > sizeof(tmp) / sizeof(tmp[0])) n = sizeof(tmp) / sizeof(tmp[0]);
    for (uint32_t i = 0; i < n; i++) {
        float s = 0; int c = 0;
        for (int j = -(int)k; j <= (int)k; j++) {
            int idx = (int)i + j;
            if (idx >= 0 && idx < (int)n) { s += env[idx]; c++; }
        }
        tmp[i] = s / (float)c;
    }
    memcpy(env, tmp, n * sizeof(float));
}