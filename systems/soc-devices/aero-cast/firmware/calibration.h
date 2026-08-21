/* calibration.h — geometry calibration and zero-wind offset storage */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <stdbool.h>

/* Initialize calibration (load from flash or defaults) */
void cal_init(void);

/* Get zero-wind offset for a path (m/s) */
float cal_get_offset(int path_idx);

/* Set zero-wind offset for a path (from calibration mode) */
void cal_set_offset(int path_idx, float offset);

/* Get calibrated path length for a path (mm) */
float cal_get_path_length(int path_idx);

/* Set calibrated path length */
void cal_set_path_length(int path_idx, float length_mm);

/* Save calibration to flash */
bool cal_save(void);

/* Run zero-wind calibration (averages N samples in still air) */
bool cal_zero_wind(int num_samples);

/* Check if calibration is valid */
bool cal_is_valid(void);

#endif /* CALIBRATION_H */