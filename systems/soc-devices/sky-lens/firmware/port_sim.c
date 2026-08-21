/*
 * port_sim.c — host simulation shim for Sky Lens
 *
 * Stubs the ESP32 HAL (RMT, ADC, I²C, FatFS, BLE, Wi-Fi, timers) so the
 * firmware's physics + math path (coincidence, zenith, skymap, lifetime,
 * pressure correction) can be compiled and run on a host with gcc/clang.
 *
 * The simulator generates synthetic cosmic-ray muon events with a
 * realistic sea-level flux (~1 cm⁻² min⁻¹), a cos²θ angular distribution,
 * a barometric pressure drift, and (in lifetime mode) a prompt-delayed
 * exponential with τ_µ = 2.197 µs. This drives the full firmware pipeline
 * (coincidence → event → zenith → skymap → lifetime fit) end-to-end.
 */
#include "sky_lens.h"
#include "coincidence.h"
#include "adc.h"
#include "sipm_bias.h"
#include "imu.h"
#include "pressure.h"
#include "skymap.h"
#include "zenith.h"
#include "lifetime.h"
#include "sdlog.h"
#include "ble.h"
#include "wifi.h"
#include "power.h"
#include "port_sim.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdarg.h>

/* ── Simulation state ────────────────────────────────────────────────── */
static uint64_t sim_time_us = 0;       /* simulated time since boot */
static uint64_t sim_end_us  = 24ULL * 3600ULL * 1000000ULL;  /* 24 hours */
static int      sim_step_ev = 0;       /* events generated this step */
static float    sim_pressure = 1013.25f;
static float    sim_temp     = 22.0f;
static float    sim_mu_rate_per_s = 0.4f;  /* ~25 cpm through 50×50 mm */
static bool     sim_lifetime_mode = false;
static bool     sim_done = false;

/* ── Logging ─────────────────────────────────────────────────────────── */
void port_sim_log(const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    printf("[sim] ");
    vprintf(fmt, ap);
    printf("\n");
    va_end(ap);
}

/* ── Time ─────────────────────────────────────────────────────────────── */
uint64_t port_sim_now_us(void) { return sim_time_us; }

/* ── Init ─────────────────────────────────────────────────────────────── */
void port_sim_init(void)
{
    sim_time_us = 0;
    sim_done = false;
    srand(42);   /* deterministic for reproducible runs */
    sim_lifetime_mode = true;   /* enable lifetime mode for the sim */
    port_sim_log("simulating 24 h of cosmic-ray muons @ %.1f cpm (lifetime mode ON)",
                 sim_mu_rate_per_s * 60.0f);
}

bool port_sim_done(void) { return sim_done; }

/* ── Date (deterministic) ────────────────────────────────────────────── */
void port_sim_date(char *buf, int len)
{
    snprintf(buf, len, "20260619");
}

/* ── Synthetic event generation ────────────────────────────────────────
 * Each step advances time by a random exponential interval (Poisson
 * process) and generates one coincidence event with:
 *   - a cos²θ zenith distribution,
 *   - a uniform azimuth,
 *   - pulse heights ~1 MeV deposit + noise,
 *   - a pressure that drifts slowly.
 * In lifetime mode, ~5% of events are prompt-delayed pairs with an
 * exponential delay of τ = 2.197 µs.
 */
static float rand_uniform(void) { return (float)rand() / (float)RAND_MAX; }

/* Inverse-CDF sample of cos²θ: θ = acos(sqrt(u)) gives a cos²θ
 * distribution in solid angle (flux ∝ cos²θ, sample cosθ ∝ cosθ). */
static float sample_zenith(void)
{
    float u = rand_uniform();
    float cost = sqrtf(u);          /* cosθ ∝ cosθ → cosθ² distribution */
    float zen = acosf(cost) * (180.0f / 3.14159265f);
    return zen;
}

void port_sim_step(void)
{
    /* Advance time by the inter-event interval (Poisson) */
    float dt_s = -logf(rand_uniform() + 1e-9f) / sim_mu_rate_per_s;
    sim_time_us += (uint64_t)(dt_s * 1e6f);

    /* Slow pressure drift: sinusoid + noise */
    sim_pressure = 1013.25f + 8.0f * sinf((float)sim_time_us * 1e-6f * 0.1f)
                   + (rand_uniform() - 0.5f) * 0.5f;
    sim_temp = 22.0f + 3.0f * sinf((float)sim_time_us * 1e-6f * 0.05f);

    /* Generate one muon event */
    float zen = sample_zenith();
    float az  = rand_uniform() * 360.0f;

    /* Δt from zenith: Δt = (d_m / c) * tanθ
     * d = 30 mm = 0.030 m, c = 3e8 m/s → Δt_s = 0.030/3e8 * tanθ = 1e-10 * tanθ
     * → dt_ps = 1e-10 * tanθ * 1e12 = 100 * tanθ (picoseconds) */
    float dt_ps = (SKY_LENS_TILE_GAP_MM * 1e-3f / 3e8f) * tanf(zen * 3.14159265f / 180.0f) * 1e12f;

    /* Pulse heights: ~1000-3000 mV (proxy for ~1 MeV deposit) */
    int16_t h0 = (int16_t)(1500 + rand_uniform() * 1500);
    int16_t h1 = (int16_t)(1500 + rand_uniform() * 1500);

    /* Feed into the coincidence path via the edge hooks.
     * Timestamps are in picoseconds. */
    int64_t ts0 = (int64_t)(sim_time_us * 1000);       /* µs → ps */
    int64_t ts1 = ts0 + (int64_t)dt_ps;                /* dt in ps */
    coincidence_on_edge0(ts0);
    coincidence_on_edge1(ts1);

    /* Inject the pulse heights via the sim ADC hook (the coincidence
     * path calls adc_trigger_and_read which calls port_sim_adc_read).
     * Set the "next" heights to be consumed by the next ADC read. */
    port_sim_set_next_adc(h0, h1);

    /* Lifetime mode: occasionally generate a prompt-delayed pair.
     * 5% of muons stop and decay; add some accidental background too. */
    if (sim_lifetime_mode) {
        if (rand_uniform() < 0.05f) {
            float delay_us = -logf(rand_uniform() + 1e-9f) * 2.197f;  /* τ_µ */
            if (delay_us < 20.0f) {
                lifetime_add_delay(delay_us);
            }
        }
        /* Accidental background: ~2% chance of a random delay 0-20 µs */
        if (rand_uniform() < 0.02f) {
            lifetime_add_delay(rand_uniform() * 20.0f);
        }
    }

    sim_step_ev++;

    /* Done after 24 hours */
    if (sim_time_us >= sim_end_us) {
        sim_done = true;
    }
}

/* ── ADC shim ─────────────────────────────────────────────────────────── */
static int16_t s_next_h0 = 2000, s_next_h1 = 2000;
void port_sim_set_next_adc(int16_t h0, int16_t h1)
{
    s_next_h0 = h0; s_next_h1 = h1;
}
void port_sim_adc_read(int16_t *h0, int16_t *h1)
{
    *h0 = s_next_h0; *h1 = s_next_h1;
}

/* ── IMU shim ─────────────────────────────────────────────────────────── */
static float sim_yaw = 0.0f;
void port_sim_imu_quat(float *w, float *x, float *y, float *z)
{
    /* Slowly rotating attitude (yaw increases with time) */
    sim_yaw = (float)sim_time_us * 1e-6f * 0.5f;   /* 0.5 rad/s */
    float half = sim_yaw * 0.5f;
    *w = cosf(half); *x = 0.0f; *y = 0.0f; *z = sinf(half);
}
void port_sim_imu_accel(float *ax, float *ay, float *az)
{ *ax = 0; *ay = 0; *az = 9.81f; }
void port_sim_imu_gyro(float *gx, float *gy, float *gz)
{ *gx = 0; *gy = 0; *gz = 0.5f; }

/* ── Pressure / temp shim ─────────────────────────────────────────────── */
float port_sim_pressure_hpa(void) { return sim_pressure; }
float port_sim_temp_c(void)       { return sim_temp; }