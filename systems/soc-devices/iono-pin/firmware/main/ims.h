/*
 * ims.h — Drift-tube ion mobility spectrometry DSP
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef IMS_H
#define IMS_H

#include <stdint.h>
#include <stdbool.h>

#define IMS_SAMPLES_PER_SWEEP   140     /* 0.5-3.5 ms @ 40 ksps */
#define IMS_AVG_COUNT           256     /* rolling-average spectra */
#define IMS_MAX_PEAKS           12
#define IMS_DRIFT_LEN_MM        85.0f
#define IMS_DRIFT_VOLTAGE_V     2125.0f
#define IMS_T_START_MS          0.5f   /* drift window start (shutter pulse) */
#define IMS_T_END_MS            3.5f

/* Raw single-sweep sample buffer (140 samples @ 40 ksps) */
typedef struct {
    int16_t raw[IMS_SAMPLES_PER_SWEEP];
} ims_sweep_t;

/* Rolling-average spectrum (32-bit accumulator + count) */
typedef struct {
    int32_t acc[IMS_SAMPLES_PER_SWEEP];
    uint16_t count;
} ims_avg_t;

/* Detected peak in K0 space */
typedef struct {
    float k0;           /* reduced mobility cm^2/(V.s) */
    float drift_ms;     /* drift time ms */
    int16_t amplitude;  /* peak height (ADC counts) */
} ims_peak_t;

/* Full spectrum result */
typedef struct {
    float pressure_kpa;     /* BME280 pressure */
    float drift_temp_c;     /* DS18B20 drift tube wall temp */
    float ambient_temp_c;   /* BME280 temp */
    ims_peak_t peaks[IMS_MAX_PEAKS];
    uint8_t num_peaks;
    float reactant_k0;       /* RIP peak K0 (should be ~2.7) */
    bool rip_present;
    int16_t spectrum[IMS_SAMPLES_PER_SWEEP]; /* averaged spectrum (for display/stream) */
} ims_result_t;

void ims_init(void);
void ims_reset_avg(void);
void ims_accumulate(const int16_t *raw);            /* add one sweep */
bool ims_result_ready(void);                         /* avg complete */
void ims_compute(float pressure_kpa, float drift_temp_c, float ambient_temp_c,
                 ims_result_t *out);                 /* extract peaks + K0 */

/* Peak detection */
uint8_t ims_detect_peaks(const int16_t *spec, uint16_t n, ims_peak_t *peaks, uint8_t max);

/* Reduced mobility computation: K0 = L^2 / (V * t) * (P/760) * (273/T) */
static inline float ims_k0(float drift_ms, float v_drift, float p_kpa, float t_c)
{
    if (drift_ms < 0.05f || v_drift < 1.0f || p_kpa < 10.0f) return 0.0f;
    float t_sec = drift_ms * 1e-3f;
    float p_torr = p_kpa * 7.50062f;     /* kPa -> mmHg (torr) */
    float t_kelvin = t_c + 273.15f;
    /* K0 = (L^2)/(V*t) * (P/760) * (273/T) ; L in cm */
    float L_cm = IMS_DRIFT_LEN_MM / 10.0f;
    return (L_cm * L_cm) / (v_drift * t_sec) * (p_torr / 760.0f) * (273.0f / t_kelvin);
}

#endif /* IMS_H */