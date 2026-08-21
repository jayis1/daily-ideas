/*
 * sdlog.h — FatFS JSON logging to microSD card
 */

#ifndef QUARTZ_TUNER_SDLOG_H
#define QUARTZ_TUNER_SDLOG_H

#include "types.h"

int sdlog_init(void);
int sdlog_save(const crystal_t *crystal);
int sdlog_list(int max_entries, uint32_t *ids);

#endif