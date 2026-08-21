/* wind.c — 3D wind vector computation and turbulence statistics
 *
 * Transforms path-projected wind components into orthogonal (u, v, w)
 * using the geometry matrix, computes sonic temperature, and accumulates
 * turbulence statistics.
 */

#include <math.h>
#include <string.h>
#include "wind.h"
#include "sonic.h"
#include "sdkconfig.h"
#include "calibration.h"

/* Geometry matrix: each row is the unit direction vector of a path
 * in (east, north, up) coordinates.
 *
 * Tripod geometry: bottom ring radius R, height H, 3 paths from bottom
 * vertices to top center.
 *
 * Path 0: from (R*cos(0°), R*sin(0°), 0) to (0, 0, H)
 *   direction = (-R, 0, H) / L
 * Path 1: from (R*cos(120°), R*sin(120°), 0) to (0, 0, H)
 *   direction = (-R*cos120, -R*sin120, H) / L
 * Path 2: from (R*cos(240°), R*sin(240°), 0) to (0, 0, H)
 *   direction = (-R*cos240, -R*sin240, H) / L
 */
static float geom_matrix[3][3];   /* direction unit vectors (rows) */
static float geom_inv[3][3];      /* inverse for solving */

static void compute_geometry(void)
{
    float R = FRAME_RADIUS_MM / 1000.0f;   /* meters */
    float H = FRAME_HEIGHT_MM / 1000.0f;
    float L = sqrtf(R*R + H*H);  /* path length */

    /* Three bottom vertices at 0°, 120°, 240° */
    for (int i = 0; i < 3; i++) {
        float angle = i * 2.0f * M_PI / 3.0f;
        float bx = R * cosf(angle);
        float by = R * sinf(angle);
        /* direction from bottom vertex to top center */
        geom_matrix[i][0] = -bx / L;   /* east (u) */
        geom_matrix[i][1] = -by / L;   /* north (v) */
        geom_matrix[i][2] =  H / L;    /* up (w) */
    }

    /* Invert 3x3 matrix using cofactor method */
    float det = geom_matrix[0][0] * (geom_matrix[1][1]*geom_matrix[2][2] - geom_matrix[1][2]*geom_matrix[2][1])
              - geom_matrix[0][1] * (geom_matrix[1][0]*geom_matrix[2][2] - geom_matrix[1][2]*geom_matrix[2][0])
              + geom_matrix[0][2] * (geom_matrix[1][0]*geom_matrix[2][1] - geom_matrix[1][1]*geom_matrix[2][0]);

    /* For symmetric tripod geometry, det should be non-zero */
    float inv_det = 1.0f / det;

    geom_inv[0][0] = (geom_matrix[1][1]*geom_matrix[2][2] - geom_matrix[1][2]*geom_matrix[2][1]) * inv_det;
    geom_inv[0][1] = (geom_matrix[0][2]*geom_matrix[2][1] - geom_matrix[0][1]*geom_matrix[2][2]) * inv_det;
    geom_inv[0][2] = (geom_matrix[0][1]*geom_matrix[1][2] - geom_matrix[0][2]*geom_matrix[1][1]) * inv_det;
    geom_inv[1][0] = (geom_matrix[1][2]*geom_matrix[2][0] - geom_matrix[1][0]*geom_matrix[2][2]) * inv_det;
    geom_inv[1][1] = (geom_matrix[0][0]*geom_matrix[2][2] - geom_matrix[0][2]*geom_matrix[2][0]) * inv_det;
    geom_inv[1][2] = (geom_matrix[0][2]*geom_matrix[1][0] - geom_matrix[0][0]*geom_matrix[1][2]) * inv_det;
    geom_inv[2][0] = (geom_matrix[1][0]*geom_matrix[2][1] - geom_matrix[1][1]*geom_matrix[2][0]) * inv_det;
    geom_inv[2][1] = (geom_matrix[0][1]*geom_matrix[2][0] - geom_matrix[0][0]*geom_matrix[2][1]) * inv_det;
    geom_inv[2][2] = (geom_matrix[0][0]*geom_matrix[1][1] - geom_matrix[0][1]*geom_matrix[1][0]) * inv_det;
}

void wind_init(void)
{
    compute_geometry();
}

void wind_compute(const sonic_sample_t *sample, wind_vector_t *wind)
{
    /* Path-projected wind components */
    float v_path[3];
    for (int i = 0; i < 3; i++)
        v_path[i] = sample->paths[i].v_path;

    /* Solve: [u, v, w] = geom_inv × v_path */
    /* Apply calibration offsets first */
    v_path[0] -= cal_get_offset(0);
    v_path[1] -= cal_get_offset(1);
    v_path[2] -= cal_get_offset(2);

    wind->u = geom_inv[0][0]*v_path[0] + geom_inv[0][1]*v_path[1] + geom_inv[0][2]*v_path[2];
    wind->v = geom_inv[1][0]*v_path[0] + geom_inv[1][1]*v_path[1] + geom_inv[1][2]*v_path[2];
    wind->w = geom_inv[2][0]*v_path[0] + geom_inv[2][1]*v_path[1] + geom_inv[2][2]*v_path[2];

    /* Horizontal wind speed and direction */
    wind->speed = sqrtf(wind->u * wind->u + wind->v * wind->v);

    /* Meteorological direction: FROM which wind blows, clockwise from north */
    /* v = north component, u = east component */
    /* dir = atan2(-u, -v) converted to [0, 360) */
    float dir_rad = atan2f(-wind->u, -wind->v);
    wind->direction = dir_rad * 180.0f / M_PI;
    if (wind->direction < 0) wind->direction += 360.0f;

    /* Mean speed of sound from all valid paths */
    float c_sum = 0;
    int c_count = 0;
    for (int i = 0; i < 3; i++) {
        if (sample->paths[i].valid && sample->paths[i].c_path > 100.0f) {
            c_sum += sample->paths[i].c_path;
            c_count++;
        }
    }
    wind->c_mean = (c_count > 0) ? c_sum / c_count : 0.0f;

    /* Sonic temperature: T = c² / (3 * R_specific)
     * R_specific for dry air = 287.05 J/(kg·K)
     * T = c² / (3 × 287.05) = c² / 861.15
     * But the standard formula uses T = c² / 403 (includes factor of ~2 for
     * the round-trip average convention). Let's use the standard:
     * T_sonic = c² / 403 (K) — this is the commonly used approximation
     * accounting for the (1 + 0.609*q) humidity factor for dry air baseline.
     */
    if (wind->c_mean > 0.1f) {
        wind->t_sonic = (wind->c_mean * wind->c_mean) / 403.0f;
    } else {
        wind->t_sonic = 0.0f;
    }
}

/* ---- Turbulence statistics ---- */

/* Internal accumulators */
typedef struct {
    double sum_u, sum_v, sum_w;
    double sum_uu, sum_vv, sum_ww;
    double sum_uw, sum_vw;
    uint32_t count;
} turb_accum_t;

static turb_accum_t accum;

void turb_init(turbulence_stats_t *stats)
{
    memset(&accum, 0, sizeof(accum));
    stats->n_samples = 0;
}

void turb_add(turbulence_stats_t *stats, const wind_vector_t *wind)
{
    accum.sum_u += wind->u;
    accum.sum_v += wind->v;
    accum.sum_w += wind->w;
    accum.sum_uu += (double)wind->u * wind->u;
    accum.sum_vv += (double)wind->v * wind->v;
    accum.sum_ww += (double)wind->w * wind->w;
    accum.sum_uw += (double)wind->u * wind->w;
    accum.sum_vw += (double)wind->v * wind->w;
    accum.count++;
    stats->n_samples = accum.count;
}

void turb_finalize(turbulence_stats_t *stats)
{
    if (accum.count < 2) {
        memset(stats, 0, sizeof(*stats));
        stats->n_samples = accum.count;
        return;
    }

    double n = (double)accum.count;

    /* Means */
    stats->u_mean = (float)(accum.sum_u / n);
    stats->v_mean = (float)(accum.sum_v / n);
    stats->w_mean = (float)(accum.sum_w / n);

    /* Variances (using sum(x²)/n - mean²) */
    float var_u = (float)(accum.sum_uu / n - (accum.sum_u / n) * (accum.sum_u / n));
    float var_v = (float)(accum.sum_vv / n - (accum.sum_v / n) * (accum.sum_v / n));
    float var_w = (float)(accum.sum_ww / n - (accum.sum_w / n) * (accum.sum_w / n));

    if (var_u < 0) var_u = 0;
    if (var_v < 0) var_v = 0;
    if (var_w < 0) var_w = 0;

    stats->sigma_u = sqrtf(var_u);
    stats->sigma_v = sqrtf(var_v);
    stats->sigma_w = sqrtf(var_w);

    /* Covariances */
    stats->u_w_cov = (float)(accum.sum_uw / n - (accum.sum_u / n) * (accum.sum_w / n));
    stats->v_w_cov = (float)(accum.sum_vw / n - (accum.sum_v / n) * (accum.sum_w / n));

    /* Turbulent Kinetic Energy: TKE = 0.5 * (σ_u² + σ_v² + σ_w²) */
    stats->tke = 0.5f * (var_u + var_v + var_w);

    /* Friction velocity: u* = sqrt(-⟨u'w'⟩) (valid when u_w_cov < 0) */
    if (stats->u_w_cov < 0) {
        stats->u_star = sqrtf(-stats->u_w_cov);
    } else {
        stats->u_star = 0.0f;  /* no valid momentum flux */
    }

    /* Turbulence intensity: TI = σ_u / |Ū| */
    float u_horiz_mean = sqrtf(stats->u_mean * stats->u_mean + stats->v_mean * stats->v_mean);
    stats->turb_intensity = (u_horiz_mean > 0.01f) ? stats->sigma_u / u_horiz_mean : 0.0f;

    stats->n_samples = accum.count;
}