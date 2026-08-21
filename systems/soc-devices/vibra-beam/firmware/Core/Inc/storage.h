/*
 * storage.h — MicroSD CSV + binary logging
 */

#ifndef STORAGE_H
#define STORAGE_H

#include <stdint.h>
#include "interferometer.h"

void storage_init(void);
void storage_log_csv(const phase_block_t *pb, uint32_t t_ms);
void storage_log_iq_bin(const iq_block_t *iq, uint32_t t_ms);
void storage_load_params(acq_params_t *p);
void storage_save_params(const acq_params_t *p);
void storage_sync(void);

#endif /* STORAGE_H */