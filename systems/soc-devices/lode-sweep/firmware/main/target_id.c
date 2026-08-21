/*
 * lode-sweep / firmware / target_id.c
 * k-NN target classifier (8 classes, 32 reference templates).
 *
 * Classifies the normalized 16-gate decay curve using a k-NN classifier
 * (k=5, Euclidean distance) against a flash library of 32 reference
 * templates spanning 8 metal classes (4 templates each).
 */
#include "main.h"

/* Reference decay curve templates: 32 templates × 16 gates.
   Each template is a normalized decay curve (0..1) for a specific
   metal class at a specific size/depth combination.
   These are synthetic but physically realistic curves based on
   published PI decay time constants for common metals. */

/* τ (µs) for each class (calibrated values, spread across the 10–284 µs
   gate range for maximum k-NN separability):
   Iron: 4 (ferromagnetic, fast + distinctive double-decay)
   Foil: 10 (thin aluminum, fast)
   Nickel: 17
   Pull-tab: 25 (aluminum alloy)
   Zinc: 35
   Gold: 45 (dense, moderate conductivity)
   Copper: 58 (high conductivity)
   Silver: 75 (very high conductivity, longest decay)
*/

/* Generate a synthetic decay curve for a given τ and noise level */
static void gen_template(float tau, float noise_amp, float *out)
{
    for (int i = 0; i < NUM_GATES; i++) {
        float t = GATE_DELAY_US[i];
        float val = expf(-t / tau);
        /* Iron has a distinctive double-decay (fast ferromagnetic + slower) */
        if (tau < 8.0f) {
            val += 0.5f * expf(-t / (tau * 0.2f));
        }
        /* Add slight noise to make templates realistic */
        val += noise_amp * (float)((i * 37 + 17) % 20 - 10) / 200.0f;
        out[i] = val;
    }
    /* Clamp to noise floor */
    for (int i = 0; i < NUM_GATES; i++) if (out[i] < 0.001f) out[i] = 0.001f;
    /* Normalize to 0..1 */
    float maxv = 0;
    for (int i = 0; i < NUM_GATES; i++) if (out[i] > maxv) maxv = out[i];
    if (maxv > 0) {
        for (int i = 0; i < NUM_GATES; i++) out[i] /= maxv;
    }
}

/* Template library: [32][16] — 3 templates per class (size/depth variations) */
static float templates[NUM_TEMPLATES][NUM_GATES];
static uint8_t template_class[NUM_TEMPLATES];

void target_id_init(void)
{
    /* Generate templates at boot (in real build, these would be in flash) */
    const float class_tau[NUM_CLASSES] = {4, 10, 17, 25, 35, 45, 58, 75};
    const float size_variation[4] = {0.9f, 0.95f, 1.0f, 1.1f};

    for (int c = 0; c < NUM_CLASSES; c++) {
        for (int v = 0; v < 4; v++) {
            int idx = c * 4 + v;
            float tau = class_tau[c] * size_variation[v];
            float noise = 0.02f * (v + 1);
            gen_template(tau, noise, templates[idx]);
            template_class[idx] = (uint8_t)c;
        }
    }
}

/*
 * Classify a normalized 16-gate decay curve using k-NN (k=5, Euclidean).
 * Sets r->target_class and r->confidence in the result struct.
 */
void target_id_classify(const float *gates, sweep_result_t *r)
{
    /* Compute distances to all 32 templates */
    float dist[NUM_TEMPLATES];
    for (int t = 0; t < NUM_TEMPLATES; t++) {
        float d = 0;
        for (int g = 0; g < NUM_GATES; g++) {
            float diff = gates[g] - templates[t][g];
            d += diff * diff;
        }
        dist[t] = sqrtf(d);
    }

    /* Find the K nearest templates (simple selection sort for K=5) */
    int knn_idx[KNN_K];
    for (int k = 0; k < KNN_K; k++) {
        float min_d = 1e9f;
        int min_i = 0;
        for (int t = 0; t < NUM_TEMPLATES; t++) {
            if (dist[t] < min_d) {
                min_d = dist[t];
                min_i = t;
            }
        }
        knn_idx[k] = min_i;
        dist[min_i] = 1e9f;   /* mark as used */
    }

    /* Vote: count class occurrences among k nearest */
    int votes[NUM_CLASSES] = {0};
    for (int k = 0; k < KNN_K; k++) {
        votes[template_class[knn_idx[k]]]++;
    }

    /* Find majority class */
    int best_class = 0, best_votes = 0;
    for (int c = 0; c < NUM_CLASSES; c++) {
        if (votes[c] > best_votes) {
            best_votes = votes[c];
            best_class = c;
        }
    }

    r->target_class = (uint8_t)best_class;
    r->confidence = (float)best_votes / (float)KNN_K;
}