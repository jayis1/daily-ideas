/* library.h — Reference library management (NVS flash storage)
 *
 * Stores up to 50 reference liquid fingerprints in NVS flash.
 * Each entry contains a label (name) and 48-feature impedance fingerprint.
 */

#ifndef TASTE_BEAD_LIBRARY_H
#define TASTE_BEAD_LIBRARY_H

#include "esp_err.h"
#include "sdkconfig.h"
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    char label[LIBRARY_MAX_NAME_LEN];
    float features[NUM_FEATURES];
    int64_t timestamp_us;
    uint16_t measurement_count;  /* how many samples averaged for this entry */
} library_entry_t;

/* Initialize library (load from NVS) */
esp_err_t library_init(void);

/* Get number of entries in library */
int library_count(void);

/* Get entry by index */
esp_err_t library_get(int index, library_entry_t *entry);

/* Add a new reference entry (returns index) */
esp_err_t library_add(const char *label,
                       const float features[NUM_FEATURES],
                       int *out_index);

/* Delete an entry by index */
esp_err_t library_delete(int index);

/* Delete all entries (clear library) */
esp_err_t library_clear(void);

/* Save library to NVS (called automatically after add/delete) */
esp_err_t library_save(void);

/* Load library from NVS */
esp_err_t library_load(void);

/* Find entry by label (returns index or -1) */
int library_find_by_label(const char *label);

/* Update an existing entry (e.g., average new measurement) */
esp_err_t library_update(int index, const float features[NUM_FEATURES]);

#endif /* TASTE_BEAD_LIBRARY_H */