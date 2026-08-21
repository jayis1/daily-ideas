/*
 * lode-sweep / firmware / depth.c
 * Depth estimation from signal amplitude, target class, and coil tilt.
 *
 * The depth estimate uses the total signal strength (sum of all 16 gates),
 * a per-class detectability coefficient, and tilt compensation from the IMU.
 * The relationship between signal amplitude and depth follows an
 * approximate 1/d³ law for a dipole coil-target interaction.
 */
#include "main.h"
#include <math.h>

/* Per-class depth coefficients K[class], calibrated on reference targets
   (e.g., coin-sized objects at known depths).
   Higher conductivity metals (silver, copper) are detectable deeper. */
static const float DEPTH_K[NUM_CLASSES] = {
    15.0f,   /* Iron     — lower detectability (ferromagnetic losses) */
    12.0f,   /* Foil     — thin, low mass */
    18.0f,   /* Nickel   */
    16.0f,   /* Pull-tab */
    17.0f,   /* Zinc     */
    20.0f,   /* Gold     — dense, moderate conductivity */
    22.0f,   /* Copper   — high conductivity */
    25.0f,   /* Silver   — highest conductivity */
};

/* Reference amplitude (volts) for a coin-sized target at 10 cm depth */
#define AMP_REF_10CM   0.5f

void depth_init(void)
{
    /* No state to initialize */
}

/*
 * Estimate depth from signal strength, target class, and coil tilt.
 *
 * depth = K[class] * (amplitude / amp_ref)^0.5 / cos(tilt)
 *
 * The square root (rather than cube root) is used because the signal
 * amplitude already integrates over 16 time gates, which partially
 * compensates for the 1/d³ spreading loss.
 *
 * Tilt compensation: a tilted coil receives less flux from the target.
 * The effective depth is divided by cos(tilt) to account for the
 * reduced coupling.
 */
void depth_estimate(sweep_result_t *r)
{
    float amp = fabsf(r->signal_strength);
    if (amp < 1e-6f) {
        r->depth_cm = 0.0f;
        return;
    }

    /* Amplitude-to-depth: sqrt relationship */
    float ratio = amp / AMP_REF_10CM;
    if (ratio > 1.0f) ratio = 1.0f;   /* clamp — very close targets */
    float raw_depth = DEPTH_K[r->target_class] * sqrtf(ratio);

    /* Tilt compensation: cos(tilt) */
    float cos_tilt = cosf(r->tilt_deg * (float)M_PI / 180.0f);
    if (cos_tilt < 0.5f) cos_tilt = 0.5f;   /* reject extreme tilt */

    r->depth_cm = raw_depth / cos_tilt;

    /* Clamp to reasonable range */
    if (r->depth_cm > 80.0f) r->depth_cm = 80.0f;
    if (r->depth_cm < 0.0f) r->depth_cm = 0.0f;
}