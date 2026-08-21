/*
 * sos.c — Speed of sound: threshold-cross ToF + d/t_f
 *
 * Algorithm:
 *   1. Find the first sample in the ToF buffer that exceeds 6σ above
 *      the pre-trigger RMS noise floor (the "arrival" sample).
 *   2. Parabolic interpolation on the 3 samples around the arrival
 *      refines the crossing to sub-sample resolution (1/10 sample).
 *   3. t_f = (arrival_sample_index / f_s) − tx_trigger_offset − probe_delay
 *   4. SOS = d / t_f (m/s), where d is the heel width in mm.
 *
 * The probe delay (transducer + cable) is calibrated from the acrylic
 * phantom measurement (SOS_phantom = 2700 m/s).
 */

#include "sos.h"
#include "stm32g474_conf.h"
#include <math.h>

static float last_tof_us = 0.0f;

void sos_init(void) { last_tof_us = 0.0f; }

float sos_compute(const uint16_t *buf, uint32_t n,
                  uint32_t tx_trigger_ts, float d_mm,
                  float probe_delay_us)
{
    /* Compute noise floor RMS from first 100 samples (pre-arrival) */
    double sum = 0.0, sum_sq = 0.0;
    uint32_t pre = 100;
    if (pre > n) pre = n;
    for (uint32_t i = 0; i < pre; ++i) {
        double v = (double)buf[i];
        sum += v;
        sum_sq += v * v;
    }
    double mean = sum / pre;
    double var  = (sum_sq / pre) - (mean * mean);
    double rms  = sqrt(var < 0 ? 0 : var);
    double thr  = mean + 6.0 * rms;   /* 6σ threshold */

    /* Find first sample above threshold (skip pre-trigger region) */
    uint32_t arrival = 0;
    for (uint32_t i = pre; i < n; ++i) {
        if ((double)buf[i] > thr) {
            arrival = i;
            break;
        }
    }
    if (arrival == 0 || arrival >= n - 1) return 0.0f;   /* No signal */

    /* Parabolic interpolation for sub-sample crossing */
    double y0 = (double)buf[arrival - 1];
    double y1 = (double)buf[arrival];
    double y2 = (double)buf[arrival + 1];
    double denom = (y0 - 2.0 * y1 + y2);
    double frac = 0.0;
    if (fabs(denom) > 1e-6) {
        frac = 0.5 * (y0 - y2) / denom;
    }
    double arrival_f = (double)arrival + frac;   /* sub-sample index */

    /* Time-of-flight in microseconds:
     *   t_arr = arrival_f / f_s  (in seconds)
     *   t_trigger_offset = (tx_trigger_ts / f_s_hrtim) (relative)
     *   t_f = t_arr − t_trigger_offset − probe_delay
     * Simplified: assume tx_trigger aligns with ADC sample 0.
     */
    double t_arr_us = (arrival_f / (double)ADC1_FULL_RATE) * 1e6;   /* µs */
    double t_f_us = t_arr_us - (double)probe_delay_us;

    if (t_f_us <= 0.0) return 0.0f;   /* Invalid */

    last_tof_us = (float)t_f_us;

    /* SOS = d / t_f  (d in mm, t_f in µs → m/s = mm/µs × 1000) */
    /* mm / µs = m/ms = 1000 m/s... actually: 1 mm/µs = 1e-3 m / 1e-6 s = 1000 m/s */
    float sos_mps = (d_mm / (float)t_f_us) * 1000.0f;

    return sos_mps;
}

float sos_get_last_tof_us(void) { return last_tof_us; }