/*
 * lode-sweep / firmware / model.c
 * Shared helpers and k-NN reference library utilities.
 */
#include "main.h"

float clampf(float v, float lo, float hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

void model_init(void)
{
    /* The k-NN template library is generated at boot in target_id_init().
       This file is reserved for future ML model weights (e.g. an int8 1D-CNN
       decay-curve classifier with finer sub-class discrimination:
       coin denomination, ring vs. nugget, ferrous vs. non-ferrous variants). */
}

/* Simple running-average smoothing for display. */
void model_smooth(float *data, uint32_t n, uint8_t k)
{
    if (k == 0 || n < (uint32_t)(2 * k + 1)) return;
    static float tmp[64];
    if (n > sizeof(tmp) / sizeof(tmp[0])) n = sizeof(tmp) / sizeof(tmp[0]);
    for (uint32_t i = 0; i < n; i++) {
        float s = 0; int c = 0;
        for (int j = -(int)k; j <= (int)k; j++) {
            int idx = (int)i + j;
            if (idx >= 0 && idx < (int)n) { s += data[idx]; c++; }
        }
        tmp[i] = s / (float)c;
    }
    memcpy(data, tmp, n * sizeof(float));
}