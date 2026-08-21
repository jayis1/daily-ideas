/*
 * display.h — SH1106 OLED display for electropherogram + results
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "quant.h"

/* Initialize SH1106 OLED (I2C1, 0x3D) */
void display_init(void);

/* Show splash screen */
void display_show_splash(const char *msg);

/* Show idle screen: HV setpoint, BGE recipe, injection mode, battery */
void display_show_idle(float hv_kv, uint8_t bge, uint8_t inj, float vbat);

/* Show status message */
void display_show_status(const char *msg);

/* Show live electropherogram */
void display_show_eph_live(const float *eph, uint32_t count,
                           float hv_kv, float current_ua);

/* Show peak table results */
void display_show_results(const ion_result_t *results, uint8_t count,
                          float temp_c, float hv_kv, uint16_t run_id);

/* Show error message */
void display_show_error(const char *msg);

#endif /* DISPLAY_H */