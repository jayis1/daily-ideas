/*
 * fluorometer.c — Fluorescence measurement engine
 *
 * Coordinates LED wheel, CCD, and reference photodiode to measure
 * fluorescence emission spectra at each excitation wavelength.
 */

#include "fluorometer.h"
#include "main.h"
#include <math.h>
#include <string.h>

/* ── Public Functions ─────────────────────────────────── */

void fluorometer_init(void)
{
    /* CCD and LED wheel are initialized separately */
}

int fluorometer_measure(ex_wavelength_t ex, const acq_params_t *params, fluor_result_t *result)
{
    if (!params || !result) return -1;

    memset(result, 0, sizeof(fluor_result_t));
    result->ex_wl = ex;
    result->ex_nm = led_wavelength_nm(ex);

    /* Safety check */
    if (!fluorometer_check_safety()) {
        return -1;
    }

    /* Move wheel to excitation position */
    if (led_wheel_goto(ex) != 0) {
        return -1;
    }

    /* Capture dark frame (LED off) */
    ccd_frame_t dark;
    ccd_capture_dark(params->integration_ms, &dark);

    /* Turn on LED */
    result->ref_counts = led_on(params->led_current_ma);

    /* Capture emission frame */
    uint16_t int_time = params->integration_ms;

    if (params->auto_expose) {
        /* Auto-exposure: find optimal integration time */
        ccd_frame_t test;
        ccd_capture(params->integration_ms, &test);
        float peak_wl;
        uint16_t peak_val;
        ccd_find_peak(&test, &peak_wl, &peak_val);

        if (peak_val > 0 && peak_val < 4000) {
            float ratio = (float)params->target_counts / (float)peak_val;
            int_time = (uint16_t)(params->integration_ms * ratio);
            if (int_time < CCD_INT_MIN_MS) int_time = CCD_INT_MIN_MS;
            if (int_time > CCD_INT_MAX_MS) int_time = CCD_INT_MAX_MS;
        } else if (peak_val >= 4000) {
            /* Saturated — reduce exposure */
            int_time = params->integration_ms / 4;
            if (int_time < CCD_INT_MIN_MS) int_time = CCD_INT_MIN_MS;
        }
    }

    ccd_capture(int_time, &result->emission);

    /* Turn off LED immediately */
    led_off();

    /* Subtract dark frame */
    ccd_subtract_dark(&result->emission, &dark);
    result->integration_ms = int_time;

    /* Find peak */
    ccd_find_peak(&result->emission, &result->peak_wl, &result->peak_intensity);

    /* Compute SNR (signal / dark noise) */
    if (dark.pixels[128] > 0) {
        result->snr = (float)result->peak_intensity / (float)(dark.pixels[128] + 1);
    } else {
        result->snr = (float)result->peak_intensity;
    }

    /* Normalize by reference */
    fluorometer_normalize(result);

    return 0;
}

int fluorometer_measure_hdr(ex_wavelength_t ex, const acq_params_t *params, fluor_result_t *result)
{
    if (!params || !result) return -1;

    /* HDR: capture at short, medium, and long exposures, combine */
    fluor_result_t short_r, medium_r, long_r;
    acq_params_t hdr_params = *params;
    int success_count = 0;

    /* Short exposure (1/4×) */
    hdr_params.integration_ms = params->integration_ms / 4;
    if (hdr_params.integration_ms < CCD_INT_MIN_MS)
        hdr_params.integration_ms = CCD_INT_MIN_MS;
    hdr_params.auto_expose = 0;
    if (fluorometer_measure(ex, &hdr_params, &short_r) == 0) {
        success_count++;
    }

    /* Medium exposure (1×) */
    hdr_params.integration_ms = params->integration_ms;
    if (fluorometer_measure(ex, &hdr_params, &medium_r) == 0) {
        success_count++;
    }

    /* Long exposure (4×) */
    hdr_params.integration_ms = params->integration_ms * 4;
    if (hdr_params.integration_ms > CCD_INT_MAX_MS)
        hdr_params.integration_ms = CCD_INT_MAX_MS;
    if (fluorometer_measure(ex, &hdr_params, &long_r) == 0) {
        success_count++;
    }

    if (success_count == 0) return -1;

    /* Combine: for each pixel, pick the non-saturated frame with highest SNR */
    memset(result, 0, sizeof(fluor_result_t));
    result->ex_wl = ex;
    result->ex_nm = led_wavelength_nm(ex);
    result->integration_ms = params->integration_ms;
    result->ref_counts = medium_r.ref_counts;

    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t s = short_r.emission.pixels[i];
        uint16_t m = medium_r.emission.pixels[i];
        uint16_t l = long_r.emission.pixels[i];

        /* Prefer long exposure if not saturated */
        if (l < 4000 && l >= m) {
            result->emission.pixels[i] = l;
        } else if (m < 4000 && m >= s) {
            result->emission.pixels[i] = m;
        } else if (s < 4000) {
            result->emission.pixels[i] = s;
        } else {
            result->emission.pixels[i] = m;  /* fallback */
        }
    }

    result->emission.valid = 1;
    ccd_find_peak(&result->emission, &result->peak_wl, &result->peak_intensity);
    result->snr = medium_r.snr;

    fluorometer_normalize(result);

    return 0;
}

void fluorometer_normalize(fluor_result_t *result)
{
    if (result->ref_counts > 0) {
        float scale = 10000.0f / (float)result->ref_counts;
        for (int i = 0; i < CCD_PIXELS; i++) {
            float v = (float)result->emission.pixels[i] * scale;
            if (v > 65535) v = 65535;
            result->emission.pixels[i] = (uint16_t)v;
        }
    }
}

int fluorometer_check_safety(void)
{
    /* Check lid interlock (reed switch) */
    if (HAL_GPIO_ReadPin(LID_INTERLOCK_GPIO, LID_INTERLOCK_PIN) == GPIO_PIN_RESET) {
        /* Lid is open — unsafe to activate UV LEDs */
        return 0;
    }
    return 1;
}