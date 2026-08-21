/* calibrate.h — Open/Short/KCl calibration for Taste Bead
 *
 * Calibration procedure:
 * 1. OPEN: probe in air (no liquid) — measures parasitic capacitance
 * 2. SHORT: all electrodes shorted together — measures parasitic resistance
 * 3. KCL: probe in 0.01 M KCl (1413 µS/cm at 25°C) — reference load
 *
 * The calibration data is used to apply OSL correction to raw measurements.
 */

#ifndef TASTE_BEAD_CALIBRATE_H
#define TASTE_BEAD_CALIBRATE_H

#include "esp_err.h"
#include "ad5941.h"
#include <stdbool.h>

typedef struct {
    bool open_done;
    bool short_done;
    bool kcl_done;
    int64_t cal_timestamp;
} calibrate_status_t;

/* Initialize calibration module */
esp_err_t calibrate_init(void);

/* Run open-circuit calibration (probe in air) */
esp_err_t calibrate_open(void);

/* Run short-circuit calibration (electrodes shorted) */
esp_err_t calibrate_short(void);

/* Run KCl standard calibration (probe in 0.01 M KCl) */
esp_err_t calibrate_kcl(void);

/* Get calibration status */
calibrate_status_t calibrate_get_status(void);

/* Save calibration to NVS */
esp_err_t calibrate_save(void);

/* Load calibration from NVS */
esp_err_t calibrate_load(void);

/* Get full calibration data */
esp_err_t calibrate_get_data(ad5941_cal_t *cal);

#endif /* TASTE_BEAD_CALIBRATE_H */