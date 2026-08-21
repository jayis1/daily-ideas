/*
 * display.h — SH1106 OLED 128x64 I2C driver
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include "ims.h"
#include "library.h"

void display_init(void);
void display_clear(void);
void display_splash(void);
void display_spectrum(const ims_result_t *r, const classify_result_t *cls);
void display_status(const char *status, float hv_v, float batt_v, float p_kpa, float t_c);
void display_idle(void);
void display_fault(const char *msg);

#endif /* DISPLAY_H */