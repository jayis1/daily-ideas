/**
 * densitometer.c — Vibrating Tube Densitometer Implementation
 * 
 * Measures specific gravity by driving a piezo-coupled stainless steel
 * tube at its resonant frequency and tracking frequency shifts that
 * correspond to changes in fluid density.
 * 
 * Physical model:
 *   f_res = (1/2π) × √(k / (m_tube + ρ_fluid × V_tube))
 * 
 * After calibration with air and water:
 *   ρ = ρ_water × (f_water² - f²) / (f_water² - f_air²)
 *   SG = ρ / ρ_water_ref (temperature corrected)
 */

#include "densitometer.h"
#include "stm32l4xx_hal.h"
#include <math.h>
#include <string.h>

/* DAC and PWM handles */
extern DAC_HandleTypeDef hdac1;
extern TIM_HandleTypeDef htim3;

/* State */
static densitometer_config_t s_config;
static densitometer_cal_t s_cal;
static densitometer_result_t s_last_result;
static bool s_initialized = false;

/* Resonance tracking */
#define MAX_FREQ_STEPS    700   /* (8000-1000)/10 */
#define RESONANCE_WINDOW  5     /* Points around peak for interpolation */

/*----------------------------------------------------------------------------*/

int densitometer_init(const densitometer_config_t *config) {
    if (config) {
        s_config = *config;
    } else {
        s_config.sweep_start_hz = 1000;
        s_config.sweep_end_hz = 8000;
        s_config.sweep_step_hz = 10;
        s_config.settle_time_us = 500;
        s_config.num_averages = 3;
    }
    
    /* Load calibration from flash */
    if (!densitometer_load_calibration(&s_cal)) {
        s_cal.valid = false;
    }
    
    /* Initialize DAC for piezo driver signal A */
    hdac1.Instance = DAC1;
    if (HAL_DAC_Start(&hdac1, DAC_CHANNEL_1) != HAL_OK) {
        return -1;
    }
    
    /* Initialize TIM3 for piezo driver signal B (complementary PWM) */
    if (HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1) != HAL_OK) {
        return -2;
    }
    
    memset(&s_last_result, 0, sizeof(s_last_result));
    s_initialized = true;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

int densitometer_read_sg(float temperature, densitometer_result_t *result) {
    if (!s_initialized || !s_cal.valid) {
        result->valid = false;
        return -1;
    }
    
    float freq_sum = 0.0f;
    float amp_sum = 0.0f;
    float q_sum = 0.0f;
    int valid_reads = 0;
    
    for (uint8_t avg = 0; avg < s_config.num_averages; avg++) {
        float freq, amp, q;
        
        if (frequency_sweep(&freq, &amp, &q) != 0) {
            continue;
        }
        
        freq_sum += freq;
        amp_sum += amp;
        q_sum += q;
        valid_reads++;
    }
    
    if (valid_reads == 0) {
        result->valid = false;
        return -2;
    }
    
    float avg_freq = freq_sum / valid_reads;
    float avg_amp = amp_sum / valid_reads;
    float avg_q = q_sum / valid_reads;
    
    /* Calculate density from resonant frequency */
    /* ρ = ρ_water × (f_water² - f²) / (f_water² - f_air²) */
    /* But normalized: SG = (f_water² - f²) / (f_water² - f_air²) */
    /* This comes from the linearized model */
    
    float f_air_sq = s_cal.f_air * s_cal.f_air;
    float f_water_sq = s_cal.f_water * s_cal.f_water;
    float f_meas_sq = avg_freq * avg_freq;
    
    /* Avoid division by zero */
    float denom = f_water_sq - f_air_sq;
    if (fabsf(denom) < 1.0f) {
        result->valid = false;
        return -3;
    }
    
    /* Calculate specific gravity */
    /* Note: this is a simplified model. In practice, we need to account
     * for the tube's contribution. The full model is:
     *   SG = (C_air² / f² - 1) / (C_air² / f_water² - 1)
     * where C_air and f_water are calibration constants.
     * For now, we use the linear approximation: */
    float sg = (f_water_sq - f_meas_sq) / (f_water_sq - f_air_sq);
    
    /* Apply temperature compensation */
    float sg_compensated = densitometer_temp_compensate(sg, temperature, s_cal.t_cal);
    
    /* Fill result */
    result->sg = sg;
    result->sg_temperature_compensated = sg_compensated;
    result->resonant_freq_hz = avg_freq;
    result->amplitude = avg_amp;
    result->q_factor = avg_q;
    result->valid = true;
    
    /* Cache last result */
    memcpy(&s_last_result, result, sizeof(s_last_result));
    
    return 0;
}

/*----------------------------------------------------------------------------*/

float densitometer_calibrate_air(void) {
    float freq, amp, q;
    
    /* Take 5 readings and average for calibration accuracy */
    float freq_sum = 0.0f;
    int valid = 0;
    
    for (int i = 0; i < 5; i++) {
        if (frequency_sweep(&freq, &amp, &q) == 0) {
            freq_sum += freq;
            valid++;
        }
        HAL_Delay(100);
    }
    
    if (valid == 0) return 0.0f;
    
    s_cal.f_air = freq_sum / valid;
    s_cal.valid = (s_cal.f_water > 0.0f);  /* Valid only if water cal exists too */
    
    return s_cal.f_air;
}

/*----------------------------------------------------------------------------*/

float densitometer_calibrate_water(float water_temp) {
    float freq, amp, q;
    
    float freq_sum = 0.0f;
    int valid = 0;
    
    for (int i = 0; i < 5; i++) {
        if (frequency_sweep(&freq, &amp, &q) == 0) {
            freq_sum += freq;
            valid++;
        }
        HAL_Delay(100);
    }
    
    if (valid == 0) return 0.0f;
    
    s_cal.f_water = freq_sum / valid;
    s_cal.t_cal = water_temp;
    s_cal.valid = (s_cal.f_air > 0.0f);  /* Valid only if air cal exists too */
    
    return s_cal.f_water;
}

/*----------------------------------------------------------------------------*/

float densitometer_temp_compensate(float sg_measured, 
                                    float t_measured, 
                                    float t_calibration) {
    /* Temperature correction formula:
     * SG_corrected = SG_measured × [1 + 0.0000025 × (T_measured - T_calibration)²]
     * 
     * This is a simplified correction. The full formula uses a polynomial
     * fit to the density-temperature curve of water:
     * 
     * For more precise correction, use the OIML polynomial:
     * ρ_w(t) = 999.842594 + 6.793952e-2×t - 9.095290e-3×t² 
     *          + 1.001685e-4×t³ - 1.120083e-6×t⁴ + 6.536332e-9×t⁵
     */
    float dt = t_measured - t_calibration;
    float correction = 1.0f + 0.0000025f * dt * dt;
    
    return sg_measured * correction;
}

/*----------------------------------------------------------------------------*/

bool densitometer_load_calibration(densitometer_cal_t *cal) {
    /* In production, this reads from STM32L4 flash page 31 */
    /* For now, return the in-memory copy */
    if (s_cal.valid) {
        memcpy(cal, &s_cal, sizeof(densitometer_cal_t));
        return true;
    }
    return false;
}

/*----------------------------------------------------------------------------*/

int densitometer_save_calibration(const densitometer_cal_t *cal) {
    /* In production, this writes to STM32L4 flash page 31 */
    /* For now, update in-memory copy */
    memcpy(&s_cal, cal, sizeof(densitometer_cal_t));
    return 0;
}

/*----------------------------------------------------------------------------*/

bool densitometer_get_last_reading(densitometer_result_t *result) {
    if (s_last_result.valid) {
        memcpy(result, &s_last_result, sizeof(densitometer_result_t));
        return true;
    }
    return false;
}

/*----------------------------------------------------------------------------*/

void densitometer_sleep(void) {
    /* Stop DAC output */
    HAL_DAC_Stop(&hdac1, DAC_CHANNEL_1);
    
    /* Stop TIM3 PWM */
    HAL_TIM_PWM_Stop(&htim3, TIM_CHANNEL_1);
}

void densitometer_wake(void) {
    /* Restart DAC and PWM */
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
}

/*----------------------------------------------------------------------------*/
/* Frequency Sweep Implementation */
/*----------------------------------------------------------------------------*/

/**
 * Perform a frequency sweep from sweep_start to sweep_end,
 * find the resonant peak, and return frequency/amplitude/Q.
 * 
 * The sweep works by:
 * 1. Setting DAC output to a sine wave at each frequency
 * 2. Measuring the ADC response amplitude from the receiver piezo
 * 3. Finding the frequency with maximum amplitude (resonance)
 * 4. Interpolating around the peak for better resolution
 * 5. Estimating Q factor from the peak width
 */
static int frequency_sweep(float *res_freq, float *res_amp, float *res_q) {
    float max_amplitude = 0.0f;
    float max_freq = s_config.sweep_start_hz;
    float amplitudes[MAX_FREQ_STEPS];
    float frequencies[MAX_FREQ_STEPS];
    int num_steps = 0;
    
    /* Sweep through frequencies */
    for (uint32_t f = s_config.sweep_start_hz; 
         f <= s_config.sweep_end_hz && num_steps < MAX_FREQ_STEPS;
         f += s_config.sweep_step_hz) {
        
        /* Set DAC frequency via TIM6 update rate */
        set_dac_frequency(f);
        
        /* Allow resonator to settle */
        HAL_DelayMicroseconds(s_config.settle_time_us);
        
        /* Measure amplitude via ADC */
        float amplitude = measure_receiver_amplitude();
        
        frequencies[num_steps] = (float)f;
        amplitudes[num_steps] = amplitude;
        num_steps++;
        
        /* Track maximum */
        if (amplitude > max_amplitude) {
            max_amplitude = amplitude;
            max_freq = (float)f;
        }
    }
    
    /* Check if we found a significant peak */
    if (max_amplitude < 0.01f) {
        return -1;  /* No resonance detected */
    }
    
    /* Find the index of the maximum */
    int max_idx = 0;
    for (int i = 0; i < num_steps; i++) {
        if (amplitudes[i] == max_amplitude) {
            max_idx = i;
            break;
        }
    }
    
    /* Parabolic interpolation around peak for sub-step accuracy */
    if (max_idx > 0 && max_idx < num_steps - 1) {
        float y0 = amplitudes[max_idx - 1];
        float y1 = amplitudes[max_idx];
        float y2 = amplitudes[max_idx + 1];
        float x1 = frequencies[max_idx - 1];
        float dx = s_config.sweep_step_hz;
        
        /* Parabolic interpolation: x_peak = x1 + dx * (y0 - y2) / (2*(y0 - 2*y1 + y2)) */
        float denom_interp = 2.0f * (y0 - 2.0f * y1 + y2);
        if (fabsf(denom_interp) > 0.001f) {
            float offset = (y0 - y2) / denom_interp;
            max_freq = x1 + offset * dx;
        }
    }
    
    /* Estimate Q factor: Q = f_res / bandwidth(-3dB) */
    float half_power = max_amplitude / 1.4142f;  /* -3dB = 1/√2 */
    float f_low = max_freq, f_high = max_freq;
    
    /* Search below peak for -3dB point */
    for (int i = max_idx; i >= 0; i--) {
        if (amplitudes[i] <= half_power) {
            f_low = frequencies[i];
            break;
        }
    }
    
    /* Search above peak for -3dB point */
    for (int i = max_idx; i < num_steps; i++) {
        if (amplitudes[i] <= half_power) {
            f_high = frequencies[i];
            break;
        }
    }
    
    float bandwidth = f_high - f_low;
    float q = (bandwidth > 1.0f) ? (max_freq / bandwidth) : 100.0f;
    
    *res_freq = max_freq;
    *res_amp = max_amplitude;
    *res_q = q;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

/**
 * Set the DAC output frequency for the piezo driver.
 * Uses TIM6 to generate sine wave samples via DMA.
 */
static void set_dac_frequency(uint32_t frequency_hz) {
    /* Calculate TIM6 period for desired frequency
     * DAC update rate = number_of_samples × frequency
     * Using 32 samples per sine period
     * TIM6_period = SystemCoreClock / (prescaler × 32 × frequency)
     */
    uint32_t samples_per_cycle = 32;
    uint32_t timer_clock = SystemCoreClock;  /* 80MHz */
    uint32_t update_rate = samples_per_cycle * frequency_hz;
    
    if (update_rate == 0) return;
    
    uint32_t prescaler = 1;
    uint32_t period = timer_clock / (prescaler * update_rate);
    
    /* Clamp to valid range */
    if (period < 1) period = 1;
    if (period > 0xFFFF) {
        prescaler = period / 0xFFFF + 1;
        period = timer_clock / (prescaler * update_rate);
    }
    
    __HAL_TIM_SET_PRESCALER(&htim6, prescaler - 1);
    __HAL_TIM_SET_AUTORELOAD(&htim6, period - 1);
    
    /* In production, the DAC DMA would be pre-loaded with a sine wave LUT */
    /* For now, we just set the frequency */
}

/*----------------------------------------------------------------------------*/

/**
 * Measure the amplitude of the receiver piezo signal.
 * Samples the ADC at high rate and computes RMS amplitude.
 */
static float measure_receiver_amplitude(void) {
    /* In production, this would:
     * 1. Configure ADC to sample the receiver piezo signal
     * 2. Take N samples at a rate ≥ 2× the drive frequency
     * 3. Compute the RMS amplitude of the signal
     * 4. Return the amplitude as a fraction of full-scale
     */
    
    /* Simplified implementation using single ADC reads */
    #define ADC_SAMPLES 64
    uint16_t samples[ADC_SAMPLES];
    float sum_sq = 0.0f;
    
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_5;  /* PA0 - receiver piezo */
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_2CYCLES_5;
    
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
    
    for (int i = 0; i < ADC_SAMPLES; i++) {
        HAL_ADC_Start(&hadc1);
        HAL_ADC_PollForConversion(&hadc1, 1);
        samples[i] = HAL_ADC_GetValue(&hadc1);
        HAL_ADC_Stop(&hadc1);
    }
    
    /* Compute RMS (removing DC offset first) */
    float mean = 0.0f;
    for (int i = 0; i < ADC_SAMPLES; i++) {
        mean += (float)samples[i];
    }
    mean /= ADC_SAMPLES;
    
    for (int i = 0; i < ADC_SAMPLES; i++) {
        float diff = (float)samples[i] - mean;
        sum_sq += diff * diff;
    }
    
    float rms = sqrtf(sum_sq / ADC_SAMPLES);
    
    /* Normalize to 0-1 range (12-bit ADC, centered at 2048) */
    return rms / 2048.0f;
}