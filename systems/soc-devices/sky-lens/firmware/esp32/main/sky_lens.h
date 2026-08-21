/*
 * Sky Lens — shared types
 * sky_lens.h
 */
#ifndef SKY_LENS_H
#define SKY_LENS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ── Geometry / config ──────────────────────────────────────────────── */
#define SKY_LENS_TILE_GAP_MM      30.0f   /* scintillator layer spacing */
#define SKY_LENS_WINDOW_NS         60     /* default coincidence window */
#define SKY_LENS_LIFETIME_WIN_US  20      /* prompt-delayed window */

#define SKYMAP_AZ_CELLS  64
#define SKYMAP_ZEN_CELLS 32
#define ZENITH_BINS      18            /* 5-degree bins, 0..90 */

/* ── Event ──────────────────────────────────────────────────────────── */
typedef struct {
    uint32_t seq;            /* monotonic event index */
    uint64_t ts_us;          /* timestamp, microseconds since boot */
    int16_t  h0_mv;          /* top-SiPM peak height (mV)            */
    int16_t  h1_mv;          /* bottom-SiPM peak height (mV)         */
    int32_t  dt_ps;          /* relative arrival delay (picoseconds)*/
    float    zenith_deg;     /* reconstructed zenith angle (deg)     */
    float    az_deg;         /* reconstructed azimuth (deg)         */
    float    q_w, q_x, q_y, q_z; /* attitude quaternion              */
    float    p_hpa;          /* pressure at event time (hPa)        */
    float    t_c;            /* temperature at event time (°C)      */
    uint8_t  flags;          /* bit0 = lifetime-prompt, bit1 = lifetime-delay */
} event_t;

/* ── Skymap ─────────────────────────────────────────────────────────── */
typedef struct {
    uint32_t cells[SKYMAP_AZ_CELLS * SKYMAP_ZEN_CELLS];
    uint32_t total;
} skymap_t;

/* ── Zenith histogram + fit ─────────────────────────────────────────── */
typedef struct {
    uint32_t bins[ZENITH_BINS];
    float    i0;              /* fitted I(0), counts/min               */
    float    chi2;
    float    residual;
} zenith_fit_t;

/* ── Lifetime histogram + fit ────────────────────────────────────────── */
#define LIFETIME_BINS  200      /* 100 ns bins, 0..20 µs */
typedef struct {
    uint32_t delays[LIFETIME_BINS];
    float    tau_us;          /* fitted lifetime (µs)                */
    float    tau_err_us;      /* 1-sigma error (µs)                  */
    float    bg_per_bin;      /* fitted flat background              */
    float    chi2;
    uint32_t n_pairs;
} lifetime_result_t;

/* ── Acquisition status ─────────────────────────────────────────────── */
typedef enum {
    ACQ_IDLE = 0,
    ACQ_ARMING,
    ACQ_RUN,
    ACQ_FAULT,
    ACQ_SLEEP,
    ACQ_LIFETIME,
} acquisition_status_t;

/* ── Daily rollup ───────────────────────────────────────────────────── */
typedef struct {
    uint64_t start_us;
    uint64_t end_us;
    uint32_t n_events;
    float    rate_raw_cpm;       /* raw coincidence rate              */
    float    rate_corr_cpm;      /* pressure-corrected rate          */
    float    mean_p_hpa;
    float    mean_t_c;
} daily_t;

#endif /* SKY_LENS_H */