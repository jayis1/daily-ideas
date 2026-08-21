/* display.h — SSD1306 OLED driver (I2C, 128x64) */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "wind.h"
#include "bme280.h"

typedef enum {
    DISP_WIND,
    DISP_GUST,
    DISP_FLUX,
    DISP_PROFILE,
    DISP_CALIBRATE,
    DISP_STREAM,
    DISP_NUM_MODES
} display_mode_t;

void display_init(void);
void display_clear(void);
void display_show_wind(const wind_vector_t *wind, const bme280_data_t *atm, float max_gust);
void display_show_gust(float max_gust, float max_dir, const wind_vector_t *current);
void display_show_flux(const turbulence_stats_t *stats, uint32_t elapsed_s);
void display_show_profile(float avg_speed, float avg_dir, uint32_t samples);
void display_show_calibrate(int path, const path_result_t *paths);
void display_show_status(const char *msg);

#endif /* DISPLAY_H */