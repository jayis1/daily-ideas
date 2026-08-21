/**
 * spiro_flow/flashlog.h — Flash session logging
 */
#ifndef SPIRO_FLOW_FLASHLOG_H
#define SPIRO_FLOW_FLASHLOG_H

#include "main.h"

int flashlog_init(void);
int flashlog_write_session(const spiro_result_t *r, const maneuver_buffer_t *m);
int flashlog_read_session(uint16_t id, spiro_result_t *r);
uint16_t flashlog_get_count(void);

#endif