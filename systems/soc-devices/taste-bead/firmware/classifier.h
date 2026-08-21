/* classifier.h — k-NN + decision tree liquid classifier
 *
 * Classifies a 48-feature impedance fingerprint against the stored
 * reference library using k-Nearest Neighbors (k=5).
 */

#ifndef TASTE_BEAD_CLASSIFIER_H
#define TASTE_BEAD_CLASSIFIER_H

#include "esp_err.h"
#include "sdkconfig.h"
#include "library.h"

typedef struct {
    char label[LIBRARY_MAX_NAME_LEN];
    float confidence;           /* 0-100% */
    float nearest_distance;     /* Euclidean distance to nearest entry */
    int lib_index;              /* index in library */
    int votes[KNN_K];           /* indices of k nearest neighbors */
    int vote_count;             /* how many k-NN votes (may be < k if small lib) */
} classifier_result_t;

/* Initialize classifier */
esp_err_t classifier_init(void);

/* Classify a feature vector */
esp_err_t classifier_classify(const float features[NUM_FEATURES],
                                classifier_result_t *result);

/* Get library size available to classifier */
int classifier_library_size(void);

#endif /* TASTE_BEAD_CLASSIFIER_H */