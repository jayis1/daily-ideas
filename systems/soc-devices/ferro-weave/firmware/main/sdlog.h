/*
 * sdlog.h — SD card CSV + JSON logging
 */
#ifndef FERRO_WEAVE_SDLOG_H
#define FERRO_WEAVE_SDLOG_H

#include "bh.h"
#include "sweep.h"

/* Write a sweep result to the SD card as two files:
 *   BH_YYYYMMDD_HHMMSS.csv   — raw H,B arrays + params
 *   BH_YYYYMMDD_HHMMSS.json  — derived quantities + metadata
 * Returns 0 on success. */
int sdlog_write(const sweep_params_t *sp, const geom_t *g,
                const float *H, const float *B, int n,
                const bh_result_t *r);

/* Mount the FAT filesystem. */
int sdlog_mount(void);

#endif /* FERRO_WEAVE_SDLOG_H */