/*
 * polarimeter.c — Core polarimetry measurement engine
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Implements the Malus's law curve fitting to determine the analyzer
 * null angle. The stepper rotates the analyzer through ±90° around an
 * estimated null, sampling the photodiode at each step. The intensity
 * vs angle data is fit to I(θ) = A + B·cos(2θ + φ) using linear least
 * squares on cos(2θ) and sin(2θ) components. The null (minimum) angle
 * is θ_min = (π - φ)/2 (mod π).
 *
 * The CORDIC coprocessor on the STM32G4 accelerates the cos/sin
 * computation during the fit.
 */
#include "stm32g4xx_hal.h"
#include <math.h>
#include "sdkconfig.h"
#include "stepper.h"
#include "photodiode.h"
#include "temperature.h"
#include "polarimeter.h"

extern DAC_HandleTypeDef hdac1;
extern CORDIC_HandleTypeDef hcordic;

static const double wavelengths[NUM_WAVELENGTHS] = {
    WAVELENGTH_405_NM, WAVELENGTH_520_NM, WAVELENGTH_589_NM
};

/* DAC channels for LED intensity (PA0=589, PA1=520, PA4=405) */
static const uint32_t dac_channels[NUM_WAVELENGTHS] = {
    DAC_CHANNEL_2,  /* PA1 → 520nm  (index 1) */
    DAC_CHANNEL_1,  /* PA0 → 589nm  (index 2) ... we map by index below */
};

/* Actually: index 0=405nm(DAC3=PA4), 1=520nm(DAC2=PA1), 2=589nm(DAC1=PA0) */
static const uint32_t led_dac_channels[3] = {
    DAC_CHANNEL_2,  /* 405nm → PA4 is not a DAC; use GPIO PWM instead. See note */
    DAC_CHANNEL_2,  /* 520nm → PA1 (DAC2) */
    DAC_CHANNEL_1,  /* 589nm → PA0 (DAC1) */
};

static uint8_t  current_wl_idx    = DEFAULT_WAVELENGTH_IDX;
static double   current_wl_nm     = WAVELENGTH_589_NM;
static bool     zeroed[3]         = {false, false, false};
static double   zero_angles[3]   = {0.0, 0.0, 0.0};
static double   last_estimate_null = 0.0;

/* ---- CORDIC cosine (q31 format: input = angle*2^31/π, output = cos*2^31) ---- */

static double cordic_cos(double angle_rad)
{
    /* Normalize angle to [-π, π] */
    double a = angle_rad;
    while (a >  M_PI) a -= 2.0 * M_PI;
    while (a < -M_PI) a += 2.0 * M_PI;

    /* CORDIC cosine expects input in q1.31 as fraction of π */
    int32_t q31_angle = (int32_t)((a / M_PI) * 2147483648.0);

    int32_t input = q31_angle;
    int32_t output = 0;

    HAL_CORDIC_CalculateSOI(&hcordic, &input, &output, 1);

    /* Output is cos in q1.31 format */
    return (double)output / 2147483648.0;
}

/* ---- LED control ---- */

static void led_on(uint8_t wl_idx)
{
    /* For 589nm (DAC1, PA0) and 520nm (DAC2, PA1), use DAC output.
     * For 405nm, we use GPIO PWM (TIM2 CH3 on PA4 — or just GPIO on
     * a simple board with a current-limiting resistor). Here we set
     * the appropriate DAC channel to LED_INTENSITY_DAC. */
    uint32_t channel = led_dac_channels[wl_idx];
    HAL_DAC_SetValue(&hdac1, channel, DAC_ALIGN_12B_R, LED_INTENSITY_DAC);
}

static void led_off(uint8_t wl_idx)
{
    uint32_t channel = led_dac_channels[wl_idx];
    HAL_DAC_SetValue(&hdac1, channel, DAC_ALIGN_12B_R, 0);
}

static void all_leds_off(void)
{
    for (int i = 0; i < NUM_WAVELENGTHS; i++)
        led_off(i);
}

/* ---- Malus's law curve fitting ---- */

double malus_fit_null(const double *angles, const double *intensities, int n)
{
    /*
     * Fit I(θ) = A + P·cos(2θ) + Q·sin(2θ)
     * where: B·cos(φ) = P, -B·sin(φ) = Q
     * → φ = atan2(-Q, P), B = sqrt(P² + Q²)
     * Null (minimum) at: θ_min = (π - φ) / 2 (mod π)
     *
     * Linear least squares: minimize Σ [I_i - A - P·cos(2θ_i) - Q·sin(2θ_i)]²
     * Normal equations (3×3):
     *   [ N       Σcos2θ    Σsin2θ  ] [A]   [ΣI    ]
     *   [ Σcos2θ  Σcos²2θ   Σcos2θ·sin2θ ] [P] = [ΣI·cos2θ]
     *   [ Σsin2θ  Σcos2θ·sin2θ  Σsin²2θ ] [Q]   [ΣI·sin2θ]
     */
    double S_c = 0, S_s = 0, S_cc = 0, S_ss = 0, S_cs = 0;
    double S_I = 0, S_Ic = 0, S_Is = 0;

    for (int i = 0; i < n; i++) {
        double theta = angles[i] * M_PI / 180.0;  /* deg → rad */
        double c = cordic_cos(2.0 * theta);
        double s = cordic_cos(2.0 * theta - M_PI_2); /* sin(2θ) = cos(2θ - π/2) */
        double I = intensities[i];

        S_c  += c;      S_s  += s;
        S_cc += c * c;   S_ss += s * s;   S_cs += c * s;
        S_I  += I;       S_Ic += I * c;    S_Is += I * s;
    }

    /* 3×3 matrix solve (Cramer's rule) */
    double N = (double)n;

    /* Determinant of coefficient matrix */
    double det = N * (S_cc * S_ss - S_cs * S_cs)
               - S_c * (S_c * S_ss - S_cs * S_s)
               + S_s * (S_c * S_cs - S_cc * S_s);

    if (fabs(det) < 1e-12) {
        /* Degenerate — return midpoint as fallback */
        double mid = (angles[0] + angles[n - 1]) / 2.0;
        return mid;
    }

    /* Cramer's rule for A, P, Q */
    double A_num = S_I * (S_cc * S_ss - S_cs * S_cs)
                 - S_Ic * (S_c * S_ss - S_cs * S_s)
                 + S_Is * (S_c * S_cs - S_cc * S_s);
    double A = A_num / det;

    double P_num = N * (S_Ic * S_ss - S_Is * S_cs)
                 - S_c * (S_I * S_ss - S_Is * S_s)
                 + S_s * (S_I * S_cs - S_Ic * S_s);
    double P = P_num / det;

    double Q_num = N * (S_cc * S_Is - S_cs * S_Ic)
                 - S_c * (S_c * S_Is - S_cs * S_I)
                 + S_s * (S_c * S_Ic - S_cc * S_I);
    double Q = Q_num / det;

    /* φ = atan2(-Q, P) → null at (π - φ)/2 */
    double phi = atan2(-Q, P);
    double theta_min = (M_PI - phi) / 2.0;  /* radians */

    /* Convert to degrees and normalize to [0, 180) */
    double theta_min_deg = theta_min * 180.0 / M_PI;
    while (theta_min_deg < 0)    theta_min_deg += 180.0;
    while (theta_min_deg >= 180) theta_min_deg -= 180.0;

    return theta_min_deg;
}

/* ---- Public API ---- */

void polarimeter_init(void)
{
    all_leds_off();
    zeroed[0] = zeroed[1] = zeroed[2] = false;
    current_wl_idx = DEFAULT_WAVELENGTH_IDX;
    current_wl_nm  = WAVELENGTH_589_NM;
    last_estimate_null = 0.0;
}

void polarimeter_set_wavelength(double nm)
{
    all_leds_off();
    for (int i = 0; i < NUM_WAVELENGTHS; i++) {
        if (fabs(wavelengths[i] - nm) < 1.0) {
            current_wl_idx = (uint8_t)i;
            current_wl_nm  = nm;
            return;
        }
    }
    /* Default to 589nm if unknown */
    current_wl_idx = DEFAULT_WAVELENGTH_IDX;
    current_wl_nm  = WAVELENGTH_589_NM;
}

double polarimeter_get_wavelength(void)
{
    return current_wl_nm;
}

void polarimeter_auto_zero(void)
{
    /* Measure null angle with empty tube for all 3 wavelengths */
    for (int wl = 0; wl < NUM_WAVELENGTHS; wl++) {
        polarimeter_set_wavelength(wavelengths[wl]);
        polarimeter_result_t r = polarimeter_measure();
        if (r.valid) {
            zero_angles[wl] = r.angle_deg;
            zeroed[wl] = true;
        }
    }
    /* Restore default wavelength */
    polarimeter_set_wavelength(WAVELENGTH_589_NM);
}

bool polarimeter_is_zeroed(void)
{
    return zeroed[current_wl_idx];
}

double polarimeter_get_zero_angle(uint8_t wl_idx)
{
    return zeroed[wl_idx] ? zero_angles[wl_idx] : 0.0;
}

polarimeter_result_t polarimeter_measure(void)
{
    polarimeter_result_t result = {0};
    result.wavelength_idx = current_wl_idx;
    result.wavelength_nm   = current_wl_nm;

    /* Turn on LED */
    led_on(current_wl_idx);
    HAL_Delay(MEASURE_SETTLE_MS);

    /* Check signal */
    if (!photodiode_signal_ok()) {
        result.valid = false;
        led_off(current_wl_idx);
        return result;
    }

    /* Sample MALUS_FIT_POINTS angles spanning ±MALUS_FIT_MAX_ANGLE
     * around the last estimated null. */
    static double angles[MALUS_FIT_POINTS];
    static double intensities[MALUS_FIT_POINTS];

    double start_angle = last_estimate_null - MALUS_FIT_MAX_ANGLE;
    double step_size   = (2.0 * MALUS_FIT_MAX_ANGLE) / (MALUS_FIT_POINTS - 1);

    for (int i = 0; i < MALUS_FIT_POINTS; i++) {
        double target = start_angle + i * step_size;
        stepper_move_to(target);
        HAL_Delay(MEASURE_SWEEP_DELAY_MS);
        angles[i]      = stepper_get_angle();
        intensities[i] = (double)photodiode_oversample(PHOTODIODE_OVERSAMPLE_N);
    }

    /* Turn off LED and de-energize stepper to save power */
    led_off(current_wl_idx);
    stepper_deenergize();

    /* Fit Malus's law curve */
    double null_angle = malus_fit_null(angles, intensities, MALUS_FIT_POINTS);
    last_estimate_null = null_angle;

    result.angle_deg    = null_angle;
    result.temperature_c = temperature_read();
    result.valid        = true;

    return result;
}

void polarimeter_measure_multi(polarimeter_result_t results[3])
{
    for (int wl = 0; wl < NUM_WAVELENGTHS; wl++) {
        polarimeter_set_wavelength(wavelengths[wl]);
        results[wl] = polarimeter_measure();
    }
    polarimeter_set_wavelength(WAVELENGTH_589_NM);
}

double polarimeter_compute_rotation(const polarimeter_result_t *result)
{
    if (!result->valid || !zeroed[result->wavelength_idx])
        return 0.0;
    return result->angle_deg - zero_angles[result->wavelength_idx];
}

double polarimeter_compute_concentration(double rotation_deg,
                                          double specific_rotation,
                                          double path_length_dm,
                                          double temperature_c,
                                          double temp_coeff)
{
    /* Temperature-correct rotation to 20°C */
    double alpha_20 = rotation_deg / (1.0 + temp_coeff * (temperature_c - REFERENCE_TEMP_C));
    /* c = α / ([α] × l) → in g/mL */
    double c = alpha_20 / (specific_rotation * path_length_dm);
    /* Convert to g/100mL (standard unit) */
    return c * 100.0;
}