/*
 * ccd_driver.h — TSL1402R 256-pixel linear CCD driver
 */

#ifndef CCD_DRIVER_H
#define CCD_DRIVER_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include "config.h"

/* CCD frame: 256 pixels, 16-bit (oversampled 12-bit) */
typedef struct {
    uint16_t pixels[CCD_PIXELS];     /* raw pixel values */
    uint16_t dark[CCD_PIXELS];       /* dark frame for subtraction */
    uint16_t integration_ms;         /* actual integration time used */
    uint8_t  saturated;              /* flag: any pixel saturated */
    uint8_t  valid;                  /* frame valid flag */
} ccd_frame_t;

/**
 * Initialize CCD driver — configure GPIO, timer for clock, ADC.
 */
void ccd_init(void);

/**
 * Capture one CCD frame.
 * @param integration_ms  Exposure time in milliseconds (10–5000)
 * @param frame           Output frame structure
 * @return 0 on success, -1 on error
 */
int ccd_capture(uint16_t integration_ms, ccd_frame_t *frame);

/**
 * Capture a dark frame (LED off, same integration time).
 * @param integration_ms  Exposure time matching the light frame
 * @param frame           Output dark frame
 */
void ccd_capture_dark(uint16_t integration_ms, ccd_frame_t *frame);

/**
 * Subtract dark frame from light frame in-place.
 * Clamps to zero if dark > light (noise).
 */
void ccd_subtract_dark(ccd_frame_t *light, const ccd_frame_t *dark);

/**
 * Convert pixel index to wavelength in nm.
 * @param pixel  Pixel index 0–255
 * @return Wavelength in nm
 */
float ccd_pixel_to_wavelength(uint16_t pixel);

/**
 * Find peak emission wavelength and intensity.
 * @param frame   CCD frame (dark-subtracted)
 * @param peak_wl Output: peak wavelength in nm
 * @param peak_val Output: peak intensity (ADC counts)
 * @return 0 on success
 */
int ccd_find_peak(const ccd_frame_t *frame, float *peak_wl, uint16_t *peak_val);

/**
 * Integrate CCD counts over a wavelength range.
 * @param frame  CCD frame (dark-subtracted)
 * @param wl_lo  Lower wavelength (nm)
 * @param wl_hi  Upper wavelength (nm)
 * @return Integrated counts
 */
uint32_t ccd_integrate_band(const ccd_frame_t *frame, float wl_lo, float wl_hi);

/**
 * Auto-exposure: find integration time that gives peak counts near target.
 * @param target_counts  Target peak ADC value (0–4095)
 * @param min_ms         Minimum integration time
 * @param max_ms         Maximum integration time
 * @return Optimal integration time in ms
 */
uint16_t ccd_auto_expose(uint16_t target_counts, uint16_t min_ms, uint16_t max_ms);

/**
 * Check for saturated pixels.
 * @param frame  CCD frame
 * @return Number of saturated pixels
 */
uint8_t ccd_check_saturated(const ccd_frame_t *frame);

#endif /* CCD_DRIVER_H */