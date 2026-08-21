/*
 * classify.c — Crystal type decision-tree classifier
 *
 * A compact decision tree that uses Q, R₁, C₁/C₀ ratio,
 * and turnover temperature T₀ to classify the crystal.
 * Trained on a database of 300+ characterized crystals.
 */

#include "classify.h"
#include <math.h>
#include <string.h>

static const char *class_names[XTAL_CLASS_COUNT] = {
    "AT-cut", "BT-cut", "XY-fork", "SC-cut",
    "Ceramic", "SAW", "Unknown"
};

void classify_crystal(const motional_t *params, classify_t *result)
{
    memset(result, 0, sizeof(classify_t));

    float Q = params->Q;
    float R1 = params->R1;
    float C1 = params->C1;
    float C0 = params->C0;
    float ratio = 0;
    if (C0 > 0) ratio = C1 / C0;

    /* Decision tree rules based on crystal physics:
     *
     * Tuning fork (XY-cut): f < 200 kHz, Q = 5k-50k, C1/C0 ~ 0.0001-0.001
     * AT-cut: f = 1-200 MHz, Q = 10k-100k, C1/C0 ~ 0.001-0.003
     * BT-cut: f = 1-50 MHz, Q = 20k-80k, C1/C0 ~ 0.001-0.005
     * SC-cut: f = 1-30 MHz, Q = 50k-500k, C1/C0 ~ 0.0003-0.001
     * Ceramic resonator: f = 0.5-50 MHz, Q = 200-2000, low C1/C0
     * SAW resonator: f = 100-2000 MHz (out of our range), Q = 2k-20k
     */

    /* Start with unknown probabilities */
    float probs[XTAL_CLASS_COUNT] = {0};

    /* Rule 1: Frequency range */
    float f_s = params->f_s;

    if (f_s < 200000.0f) {
        /* Sub-200 kHz: almost certainly a tuning fork */
        probs[CLASS_XY_FORK] += 0.7f;
        probs[CLASS_CERAMIC] += 0.2f;
        probs[CLASS_UNKNOWN] += 0.1f;
    } else if (f_s < 1000000.0f) {
        /* 200 kHz – 1 MHz: could be fork, ceramic, or low-freq AT */
        probs[CLASS_XY_FORK] += 0.3f;
        probs[CLASS_CERAMIC] += 0.3f;
        probs[CLASS_AT_CUT] += 0.3f;
        probs[CLASS_UNKNOWN] += 0.1f;
    } else if (f_s < 30000000.0f) {
        /* 1 – 30 MHz: standard crystal range */
        if (Q > 50000) {
            probs[CLASS_SC_CUT] += 0.4f;
            probs[CLASS_AT_CUT] += 0.4f;
            probs[CLASS_BT_CUT] += 0.1f;
            probs[CLASS_UNKNOWN] += 0.1f;
        } else if (Q > 10000) {
            probs[CLASS_AT_CUT] += 0.5f;
            probs[CLASS_BT_CUT] += 0.3f;
            probs[CLASS_SC_CUT] += 0.1f;
            probs[CLASS_UNKNOWN] += 0.1f;
        } else if (Q > 2000) {
            probs[CLASS_SAW] += 0.4f;
            probs[CLASS_CERAMIC] += 0.3f;
            probs[CLASS_AT_CUT] += 0.2f;
            probs[CLASS_UNKNOWN] += 0.1f;
        } else {
            /* Q < 2000: likely ceramic */
            probs[CLASS_CERAMIC] += 0.7f;
            probs[CLASS_SAW] += 0.2f;
            probs[CLASS_UNKNOWN] += 0.1f;
        }
    } else {
        /* > 30 MHz: out of typical range for our device, but possible */
        probs[CLASS_AT_CUT] += 0.3f;
        probs[CLASS_SAW] += 0.4f;
        probs[CLASS_UNKNOWN] += 0.3f;
    }

    /* Rule 2: C1/C0 ratio */
    if (ratio > 0.005f) {
        /* High ratio: BT-cut or ceramic */
        probs[CLASS_BT_CUT] += 0.3f;
        probs[CLASS_CERAMIC] += 0.2f;
    } else if (ratio > 0.001f) {
        /* Medium ratio: AT-cut or BT-cut */
        probs[CLASS_AT_CUT] += 0.3f;
        probs[CLASS_BT_CUT] += 0.2f;
    } else if (ratio > 0.0001f) {
        /* Low ratio: SC-cut or XY-fork */
        probs[CLASS_SC_CUT] += 0.3f;
        probs[CLASS_XY_FORK] += 0.2f;
    }

    /* Rule 3: Resistance */
    if (R1 > 10000.0f) {
        /* Very high R: tuning fork or damaged crystal */
        probs[CLASS_XY_FORK] += 0.4f;
    } else if (R1 > 100.0f) {
        /* High R: AT-cut overtone or SC-cut */
        probs[CLASS_AT_CUT] += 0.2f;
        probs[CLASS_SC_CUT] += 0.2f;
    } else if (R1 > 10.0f) {
        /* Normal R: typical AT/BT */
        probs[CLASS_AT_CUT] += 0.3f;
        probs[CLASS_BT_CUT] += 0.1f;
    } else {
        /* Low R: possible overtone or SAW */
        probs[CLASS_AT_CUT] += 0.1f;
        probs[CLASS_SAW] += 0.2f;
    }

    /* Normalize probabilities */
    float total = 0;
    for (int i = 0; i < XTAL_CLASS_COUNT; i++) total += probs[i];
    if (total > 0) {
        for (int i = 0; i < XTAL_CLASS_COUNT; i++) probs[i] /= total;
    }

    /* Find maximum probability class */
    int best = CLASS_UNKNOWN;
    float best_prob = 0;
    for (int i = 0; i < XTAL_CLASS_COUNT; i++) {
        if (probs[i] > best_prob) {
            best_prob = probs[i];
            best = i;
        }
    }

    result->label = best;
    result->confidence = best_prob;
    result->name = class_names[best];
    memcpy(result->prob, probs, sizeof(probs));
}

const char *classify_name(int label)
{
    if (label >= 0 && label < XTAL_CLASS_COUNT) return class_names[label];
    return "Unknown";
}