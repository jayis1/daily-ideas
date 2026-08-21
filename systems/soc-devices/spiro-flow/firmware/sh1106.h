/**
 * spiro_flow/sh1106.h — OLED display
 */
#ifndef SPIRO_FLOW_SH1106_H
#define SPIRO_FLOW_SH1106_H

#include "main.h"

int sh1106_init(void);
void sh1106_draw_idle(void);
void sh1106_draw_ready(uint8_t battery_pct);
void sh1106_draw_capture(const maneuver_buffer_t *m, float current_flow, float current_vol);
void sh1106_draw_results(const spiro_result_t *r, uint8_t battery_pct);
void sh1106_draw_settings(const patient_t *p, int field);

#endif