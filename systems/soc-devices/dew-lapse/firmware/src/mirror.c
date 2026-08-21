/* mirror.c — mirror film detection & tracking
 *
 * Combines the differential thermistor signal (primary PID setpoint)
 * with the IR-scatter detector (phase discrimination) to determine
 * whether the condensed film is liquid dew or frost, and to generate
 * a "film stability" indicator.
 */
#include "config.h"
#include "mirror.h"
#include "optics.h"
#include <math.h>

#define FILM_DT_SETPOINT_K   FILM_SETPOINT_K
#define STABLE_DT_THRESH     TRACK_STABLE_DT
#define STABLE_COUNT         TRACK_STABLE_COUNT

static int stable_count = 0;
static int phase = 0;     /* 0 = dew, 1 = frost */
static float dt_history[16];
static int   dt_idx = 0;
static int   dt_full = 0;

static float dt_slope(void)
{
    /* Compute finite-difference slope of ΔT history (K/s).
     * The ADS samples at 20 SPS but we downsample to 10 Hz here.
     * Return derivative in K/s.
     */
    if (!dt_full && dt_idx < 2) return 0.0f;
    int n = dt_full ? 16 : dt_idx;
    float first = dt_history[0];
    float last  = dt_history[(dt_idx - 1 + 16) % 16];
    float dt_sec = (n - 1) / 10.0f;
    if (dt_sec <= 0.0f) return 0.0f;
    return (last - first) / dt_sec;
}

int mirror_track(float t_mirror, float t_ref, float *setpoint)
{
    float dt = t_mirror - t_ref;

    /* Push to history */
    dt_history[dt_idx++] = dt;
    if (dt_idx >= 16) { dt_idx = 0; dt_full = 1; }

    /* The film present on the mirror produces a small negative ΔT
     * because the wet site loses heat to the latent-heat flux.
     * The setpoint we want the PID to track is a small |ΔT| that
     * corresponds to a stable thin film. */
    *setpoint = -FILM_DT_SETPOINT_K;

    /* Stability check */
    float slope = dt_slope();
    if (fabsf(slope) < STABLE_DT_THRESH) {
        stable_count++;
    } else {
        stable_count = 0;
    }
    return (stable_count >= STABLE_COUNT);
}

int mirror_phase(void)
{
    /* Below 0 °C, decide liquid vs. ice using the IR scatter signal. */
    extern float optics_scatter(void);
    float sc = optics_scatter();
    /* Frost has scatter ~3–5× dew film; threshold at 2.5× baseline. */
    if (sc > optics_scatter_baseline() * 2.5f) phase = 1;
    else                                      phase = 0;
    return phase;
}

void mirror_reset(void)
{
    stable_count = 0;
    dt_idx = 0;
    dt_full = 0;
    phase = 0;
}