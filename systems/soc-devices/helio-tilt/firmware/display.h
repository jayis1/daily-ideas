/*
 * display.h — SH1106 OLED 128×64 I2C display
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "radiometry.h"
#include "solar_pos.h"

/* Initialize I2C1 + OLED */
void display_init(void);

/* Show splash screen */
void display_show_splash(const char *msg);

/* Show idle/status screen */
void display_show_status(float dni, float aod870, float angstrom,
                          float pwv, float sun_az, float sun_el,
                          float bat_v, const char *state_name);

/* Show live tracking screen: DNI bar + AOD values */
void display_show_tracking(const radiometry_result_t *result,
                            const solar_pos_t *pos, float bat_v);

/* Show Langley calibration progress */
void display_show_langley(uint16_t points, float r2, float v0_870);

/* Show menu */
void display_show_menu(const char *items[], uint8_t count, uint8_t sel);

/* Show error message */
void display_show_error(const char *msg);

#endif /* DISPLAY_H */