/*
 * langley.c — Langley calibration regression
 *
 * During a Langley calibration run, the device measures V(λ) at
 * varying solar zenith angles (air mass m) over 2–3 hours. A linear
 * regression of ln(V) vs. m gives:
 *   ln(V) = ln(V₀) - τ × m
 * The y-intercept (m=0) gives ln(V₀), the extraterrestrial constant.
 * The slope gives -τ (total optical depth).
 *
 * Quality metric: R² > 0.99 indicates stable atmospheric conditions
 * and a valid calibration.
 *
 * The regression uses ordinary least squares (OLS):
 *   slope = Σ[(x-x̄)(y-ȳ)] / Σ[(x-x̄)²]
 *   intercept = ȳ - slope × x̄
 *   R² = [Σ((x-x̄)(y-ȳ))]² / [Σ(x-x̄)² × Σ(y-ȳ)²]
 */

#include "langley.h"
#include "stm32g474_conf.h"
#include <math.h>
#include <string.h>

#define MAX_LANGLEY_POINTS  200

static float langley_m[MAX_LANGLEY_POINTS];      /* Air mass per point */
static float langley_v[MAX_LANGLEY_POINTS][6];   /* Voltage (µV) per point per wl */
static uint16_t langley_count = 0;

void langley_reset(void)
{
    langley_count = 0;
    memset(langley_m, 0, sizeof(langley_m));
    memset(langley_v, 0, sizeof(langley_v));
}

void langley_add_point(const float voltages_uv[6], double air_mass)
{
    if (langley_count >= MAX_LANGLEY_POINTS) return;
    if (air_mass <= 0.0 || air_mass > 10.0) return;   /* Sanity check */

    langley_m[langley_count] = (float)air_mass;
    for (int i = 0; i < 6; i++)
        langley_v[langley_count][i] = voltages_uv[i];
    langley_count++;
}

void langley_regress(langley_result_t *result)
{
    memset(result, 0, sizeof(*result));
    result->num_points = langley_count;

    if (langley_count < LANGLEY_MIN_POINTS) {
        result->valid = false;
        return;
    }

    /* For each wavelength, regress ln(V) vs. m */
    for (int wl = 0; wl < 6; wl++) {
        float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0, sum_y2 = 0;
        uint16_t n_valid = 0;

        for (uint16_t i = 0; i < langley_count; i++) {
            if (langley_v[i][wl] <= 0.0f) continue;   /* Skip invalid */
            float x = langley_m[i];
            float y = logf(langley_v[i][wl]);
            sum_x  += x;
            sum_y  += y;
            sum_xy += x * y;
            sum_x2 += x * x;
            sum_y2 += y * y;
            n_valid++;
        }

        if (n_valid < LANGLEY_MIN_POINTS) {
            result->r_squared[wl] = 0.0f;
            result->v0[wl] = 0.0f;
            result->tau_total[wl] = 0.0f;
            continue;
        }

        float n = (float)n_valid;
        float mean_x = sum_x / n;
        float mean_y = sum_y / n;

        /* OLS: slope = [nΣxy - ΣxΣy] / [nΣx² - (Σx)²] */
        float denom = n * sum_x2 - sum_x * sum_x;
        if (fabsf(denom) < 1e-10f) {
            result->r_squared[wl] = 0.0f;
            continue;
        }

        float slope = (n * sum_xy - sum_x * sum_y) / denom;
        float intercept = mean_y - slope * mean_x;

        /* V₀ = exp(intercept), τ = -slope */
        result->v0[wl] = expf(intercept);
        result->tau_total[wl] = -slope;

        /* R² = [nΣxy - ΣxΣy]² / [nΣx² - (Σx)²][nΣy² - (Σy)²] */
        float denom_y = n * sum_y2 - sum_y * sum_y;
        if (fabsf(denom_y) < 1e-10f) {
            result->r_squared[wl] = 0.0f;
        } else {
            float r2 = (denom * denom_y);
            if (r2 > 0)
                result->r_squared[wl] = (n * sum_xy - sum_x * sum_y)
                    * (n * sum_xy - sum_x * sum_y) / r2;
            else
                result->r_squared[wl] = 0.0f;
        }
    }

    /* Valid only if R² > threshold for all wavelengths with valid data */
    bool all_valid = true;
    for (int wl = 0; wl < 6; wl++) {
        if (result->v0[wl] > 0.0f && result->r_squared[wl] < LANGLEY_MIN_R2)
            all_valid = false;
    }
    result->valid = all_valid;
}

bool langley_ready(void)
{
    return langley_count >= LANGLEY_MIN_POINTS;
}

uint16_t langley_point_count(void)
{
    return langley_count;
}