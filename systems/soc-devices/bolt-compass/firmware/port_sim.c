/*
 * port_sim.c — HAL stubs for the host simulation build.
 *
 * Provides stub ESP32 / FreeRTOS / SPI / I2C symbols so the detect /
 * classify / bearing / range / fft code compiles and runs on a host.
 * The sim feeds synthetic sferics into the pipeline directly (not via
 * the ADC driver), so adc.c is NOT linked into the sim — only the math
 * modules are.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

/* stubs for esp_log macros used by detect.c / range.c */
/* (provided via stubs/esp_log.h include) */

/* GPS stubs — referenced by adc.c, but adc.c is not linked into the sim.
 * Provided here for completeness. */
uint64_t gps_pps_last(void)     { return 0; }
uint64_t gps_sample_count(void) { return 0; }