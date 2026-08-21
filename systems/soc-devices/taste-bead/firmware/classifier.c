/* classifier.c — k-NN + decision tree liquid classifier
 *
 * Implements a k-Nearest Neighbors classifier (k=5) with a decision-tree
 * pre-filter for fast rule-based screening. The reference library is stored
 * in NVS flash and managed by library.c.
 *
 * Classification pipeline:
 * 1. Decision tree pre-filter: quick rules (e.g., "if R_s > 10 kΩ → non-aqueous")
 * 2. k-NN: compute Euclidean distance to all library entries
 * 3. Vote: majority label among k nearest neighbors
 * 4. Confidence: vote agreement × distance-based decay
 */

#include "classifier.h"
#include "library.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

static const char *TAG = "classifier";

/* Simple decision tree node for pre-filtering */
typedef struct {
    int feature_index;
    float threshold;
    int true_class;   /* -1 = continue to k-NN */
    int false_class;  /* -1 = continue to k-NN */
} dt_node_t;

/* Decision tree rules (example — would be tuned with training data) */
static const dt_node_t dt_rules[] = {
    /* Rule 0: if log10(R_s_Au) > 4 (R_s > 10kΩ) → likely non-aqueous/oil */
    { 0, 4.0f, -1, -1 },  /* both paths continue to k-NN */
    /* Rule 1: if log10(z_at_100hz_Au) < 2 → conductive (salt water, acid) */
    { 5, 2.0f, -1, -1 },
};

#define NUM_DT_RULES (sizeof(dt_rules) / sizeof(dt_rules[0]))

/* Euclidean distance between two feature vectors */
static float euclidean_distance(const float *a, const float *b, int n)
{
    float sum = 0.0f;
    for (int i = 0; i < n; i++) {
        float diff = a[i] - b[i];
        sum += diff * diff;
    }
    return sqrtf(sum);
}

/* Comparison function for sorting indices by distance */
typedef struct { float dist; int idx; } dist_idx_t;

static int cmp_dist_idx(const void *a, const void *b)
{
    float da = ((const dist_idx_t *)a)->dist;
    float db = ((const dist_idx_t *)b)->dist;
    return (da > db) ? 1 : (da < db) ? -1 : 0;
}

esp_err_t classifier_init(void)
{
    ESP_LOGI(TAG, "Classifier initialized (k=%d, %d features, %d max library)",
             KNN_K, NUM_FEATURES, LIBRARY_MAX_ENTRIES);
    return ESP_OK;
}

esp_err_t classifier_classify(const float features[NUM_FEATURES],
                                classifier_result_t *result)
{
    if (features == NULL || result == NULL) return ESP_ERR_INVALID_ARG;

    memset(result, 0, sizeof(*result));

    int lib_count = library_count();
    if (lib_count == 0) {
        strcpy(result->label, "No library");
        result->confidence = 0;
        result->nearest_distance = INFINITY;
        return ESP_ERR_NOT_FOUND;
    }

    /* Step 1: Decision tree pre-filter (currently passthrough) */
    int dt_result = -1;
    for (int i = 0; i < NUM_DT_RULES; i++) {
        const dt_node_t *rule = &dt_rules[i];
        if (rule->feature_index < 0 || rule->feature_index >= NUM_FEATURES)
            continue;
        if (features[rule->feature_index] > rule->threshold) {
            dt_result = rule->true_class;
        } else {
            dt_result = rule->false_class;
        }
        if (dt_result >= 0) break; /* early exit if decision made */
    }
    /* For now, dt_result is -1 (always go to k-NN) */

    /* Step 2: k-NN — compute distance to all library entries */
    dist_idx_t distances[LIBRARY_MAX_ENTRIES];
    int n_valid = 0;

    library_entry_t entry;
    for (int i = 0; i < lib_count && i < LIBRARY_MAX_ENTRIES; i++) {
        if (library_get(i, &entry) != ESP_OK) continue;

        float d = euclidean_distance(features, entry.features, NUM_FEATURES);
        distances[n_valid].dist = d;
        distances[n_valid].idx = i;
        n_valid++;
    }

    if (n_valid == 0) {
        strcpy(result->label, "Library error");
        result->confidence = 0;
        return ESP_FAIL;
    }

    /* Sort by distance (ascending) */
    qsort(distances, n_valid, sizeof(dist_idx_t), cmp_dist_idx);

    /* Step 3: Vote among k nearest */
    int k = KNN_K;
    if (k > n_valid) k = n_valid;

    /* Collect votes */
    int vote_indices[KNN_K];
    char vote_labels[KNN_K][LIBRARY_MAX_NAME_LEN];
    for (int j = 0; j < k; j++) {
        vote_indices[j] = distances[j].idx;
        library_get(distances[j].idx, &entry);
        strncpy(vote_labels[j], entry.label, LIBRARY_MAX_NAME_LEN - 1);
        vote_labels[j][LIBRARY_MAX_NAME_LEN - 1] = '\0';
        result->votes[j] = distances[j].idx;
    }
    result->vote_count = k;
    result->nearest_distance = distances[0].dist;

    /* Find majority label */
    int max_votes = 0;
    char majority_label[LIBRARY_MAX_NAME_LEN] = "";
    for (int j = 0; j < k; j++) {
        int count = 1;
        for (int m = j + 1; m < k; m++) {
            if (strcmp(vote_labels[j], vote_labels[m]) == 0) count++;
        }
        if (count > max_votes) {
            max_votes = count;
            strncpy(majority_label, vote_labels[j], LIBRARY_MAX_NAME_LEN - 1);
            majority_label[LIBRARY_MAX_NAME_LEN - 1] = '\0';
        }
    }

    strncpy(result->label, majority_label, LIBRARY_MAX_NAME_LEN - 1);
    result->label[LIBRARY_MAX_NAME_LEN - 1] = '\0';
    result->lib_index = distances[0].idx;

    /* Confidence = (majority votes / k) × distance-decay factor */
    float vote_confidence = (float)max_votes / (float)k * 100.0f;

    /* Distance decay: closer neighbors → higher confidence */
    float mean_dist = 0;
    for (int j = 0; j < k; j++) mean_dist += distances[j].dist;
    mean_dist /= k;

    /* Decay: confidence halves every 5 units of mean distance */
    float decay = 1.0f / (1.0f + mean_dist / 5.0f);
    result->confidence = vote_confidence * decay;

    /* Clamp confidence to 0-100 */
    if (result->confidence > 100.0f) result->confidence = 100.0f;
    if (result->confidence < 0.0f) result->confidence = 0.0f;

    /* If confidence below threshold, mark as uncertain */
    if (result->confidence < CONFIDENCE_THRESHOLD) {
        strcat(result->label, " (uncertain)");
    }

    ESP_LOGI(TAG, "Classified: %s (%.1f%%, dist=%.2f, k=%d/%d)",
             result->label, result->confidence, result->nearest_distance,
             k, KNN_K);

    return ESP_OK;
}

int classifier_library_size(void)
{
    return library_count();
}