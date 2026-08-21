/*
 * ccd_driver.c — TSL1402R 256-pixel linear CCD driver
 *
 * The TSL1402R is an analog linear CCD with 256 pixels.
 * It uses a simple SI (start) + CLK (clock) interface.
 * Each pixel charge is shifted out sequentially as an analog voltage.
 *
 * Timing:
 *   SI pulse: min 100ns high
 *   CLK: min 500ns period (2 MHz max)
 *   Pixel readout: 256 clocks after SI
 *   Integration: between SI pulse and first CLK
 *
 * We use TIM3_CH1 for clock generation and ADC2 for analog readout.
 */

#include "ccd_driver.h"
#include "main.h"
#include <math.h>

extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc2;

/* ── Private variables ────────────────────────────────── */
static uint8_t ccd_initialized = 0;

/* ── Private helpers ──────────────────────────────────── */
static void ccd_clock_pulse(void)
{
    /* Manual clock pulse for integration/start */
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_SET);
    for (volatile int i = 0; i < 5; i++);  /* ~100ns at 170MHz */
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_RESET);
    for (volatile int i = 0; i < 5; i++);
}

static void ccd_si_pulse(void)
{
    /* SI pulse: rise while CLK low, hold >100ns, fall while CLK low */
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_RESET);
    for (volatile int i = 0; i < 3; i++);
    HAL_GPIO_WritePin(CCD_SI_GPIO, CCD_SI_PIN, GPIO_PIN_SET);
    for (volatile int i = 0; i < 5; i++);  /* ~100ns */
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_SET);
    for (volatile int i = 0; i < 3; i++);
    HAL_GPIO_WritePin(CCD_SI_GPIO, CCD_SI_PIN, GPIO_PIN_RESET);
    for (volatile int i = 0; i < 3; i++);
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_RESET);
}

static uint16_t ccd_read_adc(void)
{
    /* Read one ADC sample from ADC2 (CCD analog output on PA3) */
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 10);
    return (uint16_t)HAL_ADC_GetValue(&hadc2);
}

/* ── Public Functions ─────────────────────────────────── */

void ccd_init(void)
{
    /* Ensure pins are in known state */
    HAL_GPIO_WritePin(CCD_SI_GPIO, CCD_SI_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_RESET);

    /* Give CCD time to stabilize (internal buffer startup) */
    HAL_Delay(10);

    /* Do one dummy read to clear the CCD */
    ccd_frame_t dummy;
    ccd_capture(50, &dummy);

    ccd_initialized = 1;
}

int ccd_capture(uint16_t integration_ms, ccd_frame_t *frame)
{
    if (!frame) return -1;

    memset(frame, 0, sizeof(ccd_frame_t));
    frame->integration_ms = integration_ms;

    /* 1. Issue SI pulse to start integration and clear previous frame */
    ccd_si_pulse();

    /* 2. Wait for integration time (LED on during this period, controlled by caller) */
    HAL_Delay(integration_ms);

    /* 3. Issue second SI pulse to end integration and start readout */
    ccd_si_pulse();

    /* 4. Read 256 pixels: each pixel requires one clock cycle + ADC sample */
    for (int i = 0; i < CCD_PIXELS; i++) {
        /* Clock high → pixel output valid */
        HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_SET);
        for (volatile int j = 0; j < 3; j++);  /* settle ~60ns */

        /* Oversample: take N samples and average for higher resolution */
        uint32_t sum = 0;
        for (int s = 0; s < CCD_ADC_OVERSAMPLE; s++) {
            sum += ccd_read_adc();
        }
        frame->pixels[i] = (uint16_t)(sum / CCD_ADC_OVERSAMPLE);

        /* Clock low → advance to next pixel */
        HAL_GPIO_WritePin(CCD_CLK_GPIO, CCD_CLK_PIN, GPIO_PIN_RESET);
        for (volatile int j = 0; j < 3; j++);
    }

    /* 5. Extra clocks to flush shift register */
    for (int i = 0; i < 4; i++) {
        ccd_clock_pulse();
    }

    /* Check for saturation */
    frame->saturated = ccd_check_saturated(frame);
    frame->valid = 1;

    return 0;
}

void ccd_capture_dark(uint16_t integration_ms, ccd_frame_t *frame)
{
    /* Capture with LED off — measures dark current + electronic offset */
    ccd_capture(integration_ms, frame);
    memcpy(frame->dark, frame->pixels, sizeof(frame->dark));
}

void ccd_subtract_dark(ccd_frame_t *light, const ccd_frame_t *dark)
{
    for (int i = 0; i < CCD_PIXELS; i++) {
        if (light->pixels[i] >= dark->pixels[i]) {
            light->pixels[i] -= dark->pixels[i];
        } else {
            light->pixels[i] = 0;
        }
    }
}

float ccd_pixel_to_wavelength(uint16_t pixel)
{
    /* Polynomial calibration: λ = c0 + c1*p + c2*p² */
    float p = (float)pixel;
    return CCD_WL_C0 + CCD_WL_C1 * p + CCD_WL_C2 * p * p;
}

int ccd_find_peak(const ccd_frame_t *frame, float *peak_wl, uint16_t *peak_val)
{
    if (!frame || !frame->valid) return -1;

    uint16_t max_val = 0;
    int max_idx = 0;

    /* Skip first/last 10 pixels (edge artifacts) */
    for (int i = 10; i < CCD_PIXELS - 10; i++) {
        if (frame->pixels[i] > max_val) {
            max_val = frame->pixels[i];
            max_idx = i;
        }
    }

    if (peak_wl) *peak_wl = ccd_pixel_to_wavelength(max_idx);
    if (peak_val) *peak_val = max_val;
    return 0;
}

uint32_t ccd_integrate_band(const ccd_frame_t *frame, float wl_lo, float wl_hi)
{
    if (!frame) return 0;
    uint32_t sum = 0;
    for (int i = 0; i < CCD_PIXELS; i++) {
        float wl = ccd_pixel_to_wavelength(i);
        if (wl >= wl_lo && wl <= wl_hi) {
            sum += frame->pixels[i];
        }
    }
    return sum;
}

uint16_t ccd_auto_expose(uint16_t target_counts, uint16_t min_ms, uint16_t max_ms)
{
    /* Binary search for optimal integration time */
    uint16_t lo = min_ms;
    uint16_t hi = max_ms;

    /* Quick test at mid-point */
    uint16_t mid = (lo + hi) / 2;
    ccd_frame_t test;

    /* Use current LED position */
    ccd_capture(mid, &test);

    float peak_wl;
    uint16_t peak_val;
    ccd_find_peak(&test, &peak_wl, &peak_val);

    /* Adjust based on peak value */
    if (peak_val > target_counts * 0.9f && peak_val < target_counts * 1.1f) {
        return mid;  /* Good enough */
    }

    /* Estimate needed exposure time */
    if (peak_val > 0) {
        float ratio = (float)target_counts / (float)peak_val;
        uint16_t new_time = (uint16_t)(mid * ratio);
        if (new_time < min_ms) new_time = min_ms;
        if (new_time > max_ms) new_time = max_ms;
        return new_time;
    }

    /* Fallback: use max exposure */
    return max_ms;
}

uint8_t ccd_check_saturated(const ccd_frame_t *frame)
{
    uint8_t count = 0;
    for (int i = 0; i < CCD_PIXELS; i++) {
        if (frame->pixels[i] >= 4090) count++;
    }
    return count;
}