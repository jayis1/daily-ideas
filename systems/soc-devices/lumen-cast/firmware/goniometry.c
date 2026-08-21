/**
 * lumen_cast/firmware/goniometry.c — Photometric computation
 *
 * Computes luminous flux by spherical integration, beam angle (FWHM),
 * field angle, peak candela, center-beam candlepower, beam uniformity,
 * throw distance, and color uniformity metrics.
 *
 * Uses CORDIC coprocessor for fast sin/cos where available.
 */

#include "main.h"
#include "goniometry.h"
#include <math.h>
#include <string.h>

#define TAG "GONIO"
#define PI  3.14159265358979f
#define DEG2RAD (PI / 180.0f)

/* ── Spherical integration of luminous flux ────────────────────────── */
/*
 * Φ (lm) = ∮ I(θ,φ) dΩ = Σ I(θᵢ, φⱼ) × sin(θᵢ) × Δθ × Δφ
 *
 * θ = polar angle (0 = north pole / +Y, 180 = south pole)
 * φ = azimuth angle (0–360°)
 * dΩ = sin(θ) dθ dφ  (solid angle element)
 */
float goniometry_integrate_flux(const scan_buffer_t *s)
{
    if (s->n_samples < 2)
        return 0.0f;

    const scan_config_t *cfg = &s->config;

    /* Angular step sizes in radians */
    float dtheta = (cfg->el_end - cfg->el_start) * DEG2RAD /
                   (float)(cfg->el_steps > 1 ? cfg->el_steps - 1 : 1);
    float dphi = (cfg->az_end - cfg->az_start) * DEG2RAD /
                 (float)(cfg->az_steps > 1 ? cfg->az_steps : 1);

    /* If only azimuth sweep (Type A), flux = 2π × ∫ I(φ) dφ / (2π)
     * For a 1D azimuth sweep at equator, approximate as:
     * Φ ≈ 2π × mean(I) × sin(90°) × dphi → full ring
     * More accurately: Φ ≈ Σ I × dphi × dtheta_eff
     * For equator-only sweep, use the mean-ring approximation.
     */
    if (cfg->el_steps <= 1) {
        /* 1D azimuth sweep — assume axisymmetric flux distribution.
         * Integrate I(φ) over full azimuth, multiply by 2 (upper+lower hemisphere)
         * weighted by sin(θ). For equator (θ=90°), sin=1.
         * Approximate full sphere: Φ ≈ 2π × (2/π) × ∫₀^π I(θ) sin(θ) dθ
         * For rotationally symmetric: Φ = 2π ∫ I(θ) sin(θ) dθ
         * Here we only have the equator slice, so:
         * Φ ≈ 4π × mean(I)  (rough sphere average) */
        float sum_I = 0;
        for (int i = 0; i < s->n_samples; i++)
            sum_I += s->samples[i].candela;
        float mean_I = sum_I / s->n_samples;
        /* For Type A full rotation at equator:
         * Φ = ∫₀²π I(φ) dφ × ∫₀^π sin(θ) dθ / (2π) ... not quite right
         * Better: the azimuth integral gives the equatorial ring flux.
         * Total flux ≈ 2 × mean_I × 2π (assuming symmetry above/below equator)
         * This is an approximation valid for near-symmetric sources. */
        return mean_I * 4.0f * PI;
    }

    /* 2D integration: Σ I(θ,φ) sin(θ) Δθ Δφ */
    float flux = 0.0f;
    for (int i = 0; i < s->n_samples; i++) {
        float theta = s->samples[i].elevation_deg * DEG2RAD;
        float I = s->samples[i].candela;
        flux += I * sinf(theta) * dtheta * dphi;
    }

    return flux;
}

/* ── Find peak luminous intensity ──────────────────────────────────── */

void goniometry_find_peak(const scan_buffer_t *s, float *peak_cd,
                           float *az, float *el)
{
    float max_cd = 0;
    float max_az = 0, max_el = 90;

    for (int i = 0; i < s->n_samples; i++) {
        if (s->samples[i].candela > max_cd) {
            max_cd = s->samples[i].candela;
            max_az = s->samples[i].azimuth_deg;
            max_el = s->samples[i].elevation_deg;
        }
    }

    *peak_cd = max_cd;
    *az = max_az;
    *el = max_el;
}

/* ── Beam angle (FWHM) ─────────────────────────────────────────────── */
/*
 * Finds the full width at half maximum of the luminous intensity
 * distribution. For 2D scans, computes in the meridian plane through
 * the peak. For 1D scans, finds the two crossing points of 0.5×I_max.
 */
float goniometry_beam_angle(const scan_buffer_t *s, float fraction)
{
    if (s->n_samples < 2)
        return 0.0f;

    float peak_cd, peak_az, peak_el;
    goniometry_find_peak(s, &peak_cd, &peak_az, &peak_el);

    float threshold = peak_cd * fraction;
    if (threshold < 0.01f)
        return 0.0f;

    const scan_config_t *cfg = &s->config;

    if (cfg->el_steps <= 1) {
        /* 1D azimuth sweep — find FWHM in azimuth */
        float first_cross = -1, last_cross = -1;
        for (int i = 0; i < s->n_samples - 1; i++) {
            float I0 = s->samples[i].candela;
            float I1 = s->samples[i + 1].candela;
            if ((I0 < threshold && I1 >= threshold) ||
                (I0 >= threshold && I1 < threshold)) {
                /* Linear interpolation for crossing angle */
                float frac = (threshold - I0) / (I1 - I0 + 0.0001f);
                float angle = s->samples[i].azimuth_deg +
                              frac * (s->samples[i + 1].azimuth_deg -
                                      s->samples[i].azimuth_deg);
                if (first_cross < 0)
                    first_cross = angle;
                last_cross = angle;
            }
        }
        if (first_cross >= 0 && last_cross >= 0)
            return last_cross - first_cross;
        return 360.0f;  /* never drops below threshold → very wide */
    }

    /* 2D scan — find beam angle in the elevation cut through peak azimuth */
    float first_cross = -1, last_cross = -1;
    for (int i = 0; i < s->n_samples - 1; i++) {
        /* Only look at samples near peak azimuth (within 1 step) */
        float daz = fabsf(s->samples[i].azimuth_deg - peak_az);
        if (daz > cfg->step_deg * 0.6f && daz < 360.0f - cfg->step_deg * 0.6f)
            continue;

        float I0 = s->samples[i].candela;
        float I1 = s->samples[i + 1].candela;
        if ((I0 < threshold && I1 >= threshold) ||
            (I0 >= threshold && I1 < threshold)) {
            float frac = (threshold - I0) / (I1 - I0 + 0.0001f);
            float angle = s->samples[i].elevation_deg +
                          frac * (s->samples[i + 1].elevation_deg -
                                  s->samples[i].elevation_deg);
            if (first_cross < 0)
                first_cross = angle;
            last_cross = angle;
        }
    }

    if (first_cross >= 0 && last_cross >= 0)
        return last_cross - first_cross;
    return 180.0f;
}

/* ── Beam uniformity (min/max within FWHM cone) ────────────────────── */

static float beam_uniformity(const scan_buffer_t *s, float beam_angle)
{
    float peak_cd, peak_az, peak_el;
    goniometry_find_peak(s, &peak_cd, &peak_az, &peak_el);

    float threshold = peak_cd * 0.5f;
    float min_cd = 1e9f, max_cd = 0;

    for (int i = 0; i < s->n_samples; i++) {
        if (s->samples[i].candela >= threshold) {
            if (s->samples[i].candela < min_cd)
                min_cd = s->samples[i].candela;
            if (s->samples[i].candela > max_cd)
                max_cd = s->samples[i].candela;
        }
    }

    if (max_cd < 0.01f)
        return 0.0f;
    return min_cd / max_cd;
}

/* ── Center beam candlepower (on-axis intensity) ───────────────────── */

static float center_beam_candlepower(const scan_buffer_t *s)
{
    /* Find sample closest to θ=90°, φ=0° (on-axis) */
    float best_cd = 0;
    float best_dist = 1e9f;

    for (int i = 0; i < s->n_samples; i++) {
        float d_el = fabsf(s->samples[i].elevation_deg - 90.0f);
        float d_az = fabsf(s->samples[i].azimuth_deg);
        if (d_az > 180) d_az = 360 - d_az;
        float dist = d_el + d_az;
        if (dist < best_dist) {
            best_dist = dist;
            best_cd = s->samples[i].candela;
        }
    }
    return best_cd;
}

/* ── Throw distance (to 0.25 lux) ──────────────────────────────────── */
/*
 * For flashlights: d = sqrt(I_peak / E_target)
 * where E_target = 0.25 lux (ANSI/NEMA FL-1 standard)
 */
static float throw_distance(float peak_cd)
{
    return sqrtf(peak_cd / 0.25f);
}

/* ── Color uniformity ──────────────────────────────────────────────── */

static void color_uniformity(const scan_buffer_t *s,
                              float *cct_on, float *duv_on,
                              float *cct_edge, float *duv_edge,
                              float *delta_cct, float *macadam)
{
    float peak_cd, peak_az, peak_el;
    goniometry_find_peak(s, &peak_cd, &peak_az, &peak_el);
    float threshold = peak_cd * 0.5f;

    float onaxis_cct = 0, onaxis_duv = 0;
    float best_dist = 1e9f;

    /* On-axis: closest to beam center */
    for (int i = 0; i < s->n_samples; i++) {
        float d_el = fabsf(s->samples[i].elevation_deg - peak_el);
        float d_az = fabsf(s->samples[i].azimuth_deg - peak_az);
        if (d_az > 180) d_az = 360 - d_az;
        float dist = d_el + d_az;
        if (dist < best_dist) {
            best_dist = dist;
            onaxis_cct = s->samples[i].cct_k;
            onaxis_duv = s->samples[i].duv;
        }
    }

    /* Edge: average of samples near FWHM boundary */
    float edge_cct_sum = 0, edge_duv_sum = 0;
    int edge_count = 0;
    for (int i = 0; i < s->n_samples; i++) {
        float I = s->samples[i].candela;
        if (I > peak_cd * 0.45f && I < peak_cd * 0.55f) {
            edge_cct_sum += s->samples[i].cct_k;
            edge_duv_sum += s->samples[i].duv;
            edge_count++;
        }
    }

    float edge_cct = edge_count > 0 ? edge_cct_sum / edge_count : onaxis_cct;
    float edge_duv = edge_count > 0 ? edge_duv_sum / edge_count : onaxis_duv;

    *cct_on = onaxis_cct;
    *duv_on = onaxis_duv;
    *cct_edge = edge_cct;
    *duv_edge = edge_duv;
    *delta_cct = fabsf(edge_cct - onaxis_cct);

    /* MacAdam ellipse step ≈ |Duv_edge - Duv_onaxis| / 0.001  (approx) */
    *macadam = fabsf(edge_duv - onaxis_duv) / 0.001f;
}

/* ── Main goniometry computation ───────────────────────────────────── */

void goniometry_compute(scan_buffer_t *s, photo_result_t *r)
{
    memset(r, 0, sizeof(*r));
    r->valid = false;

    if (s->n_samples < 4) {
        LOGE(TAG, "Too few samples (%d)", s->n_samples);
        return;
    }

    /* Luminous flux */
    r->luminous_flux_lm = goniometry_integrate_flux(s);

    /* Peak candela and position */
    goniometry_find_peak(s, &r->peak_candela, &r->peak_az_deg, &r->peak_el_deg);

    /* Beam angle (FWHM = 50%) */
    r->beam_angle_fwhm = goniometry_beam_angle(s, 0.5f);

    /* Field angle (10%) */
    r->field_angle_10pct = goniometry_beam_angle(s, 0.1f);

    /* Center beam candlepower */
    r->cbcp_candela = center_beam_candlepower(s);

    /* Beam uniformity */
    r->beam_uniformity = beam_uniformity(s, r->beam_angle_fwhm);

    /* Throw (ANSI FL-1: distance to 0.25 lux) */
    r->throw_m = throw_distance(r->peak_candela);

    /* Color uniformity */
    color_uniformity(s, &r->cct_onaxis_k, &r->duv_onaxis,
                     &r->cct_edge_k, &r->duv_edge,
                     &r->delta_cct_k, &r->macadam_steps_edge);

    r->valid = true;

    LOGI(TAG, "Φ=%.1f lm  Ipk=%.0f cd  beam=%.1f°  throw=%.1f m",
         r->luminous_flux_lm, r->peak_candela,
         r->beam_angle_fwhm, r->throw_m);
    LOGI(TAG, "CCT: %.0f K (axis) / %.0f K (edge)  ΔCCT=%.0f K  Duv=%.4f",
         r->cct_onaxis_k, r->cct_edge_k, r->delta_cct_k, r->duv_onaxis);
}