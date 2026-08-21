/*
 * storage.h — SD card CSV logging + W25Q128 parameter storage
 */

#ifndef STORAGE_H
#define STORAGE_H

#include "config.h"

/* SD card logging */
int  storage_init(void);
int  storage_open_log(const char *filename);
int  storage_log_result(const qcm_result_t *r);
int  storage_log_sweep(const overtone_sweep_t *s);
int  storage_log_raw(const char *line);
void storage_close_log(void);
int  storage_is_present(void);

/* W25Q128 parameter storage */
int  storage_save_params(const acq_params_t *params);
int  storage_load_params(acq_params_t *params);

/* Format helpers */
void result_to_csv(const qcm_result_t *r, char *buf, uint16_t len);
void sweep_to_csv(const overtone_sweep_t *s, char *buf, uint16_t len);

#endif /* STORAGE_H */