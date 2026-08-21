/* sd_log.h — SD card CSV logging for Taste Bead */

#ifndef TASTE_BEAD_SD_LOG_H
#define TASTE_BEAD_SD_LOG_H

#include "esp_err.h"
#include "eis.h"
#include "library.h"

/* Initialize SD card */
esp_err_t sd_init(void);

/* Open a new log file (with timestamped filename) */
esp_err_t sd_open_log(void);

/* Log a full measurement with classification result */
esp_err_t sd_log_measurement(const eis_result_t *eis,
                               const float features[NUM_FEATURES],
                               const void *result,
                               const void *ambient);

/* Close log file */
esp_err_t sd_close_log(void);

/* Check if SD card is present */
bool sd_is_present(void);

#endif /* TASTE_BEAD_SD_LOG_H */