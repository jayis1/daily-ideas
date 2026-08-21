/*
 * main_sim.c — Bolt Compass host simulation
 *
 * Generates synthetic CG and IC sferics with known bearing + distance,
 * injects them into a fake ring, runs the detect → classify → bearing →
 * range pipeline, and prints the recovered (type, bearing, distance)
 * vs. the ground truth. This is a self-test of the math path that runs
 * with no ESP-IDF and no hardware:
 *
 *   cmake -B build-sim -S sim && cmake --build build-sim
 *   ./build-sim/bolt_compass_sim
 */
#include "types.h"
#include "detect.h"
#include "classify.h"
#include "bearing.h"
#include "range.h"
#include "fft.h"
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

static ring_t g_ring;
static sample_t g_ringbuf[RING_LEN];

static void ring_reset(void)
{
    memset(g_ringbuf, 0, sizeof(g_ringbuf));
    g_ring.buf = g_ringbuf;
    g_ring.wr  = 0;
    g_ring.ts_us = 0;
}

/* Inject a synthetic sferic into the ring at a given bearing (deg),
 * distance (km), and type (0=CG, 1=IC). The Earth-ionosphere model
 * attenuates the amplitude with distance; the two loops get cos/sin
 * of the bearing; the slow-E channel gets the CG/IC signature. */
static void inject_sferic(float bearing, float dist_km, int type,
                          const range_model_t *m)
{
    /* Reference peak field at 100 km, then attenuate with distance. */
    float e_ref = m->ref_field_uv;
    float alpha = 0.00075f;   /* AVG ground, day */
    float e_peak = e_ref * expf(-alpha * dist_km) * sqrtf(100.0f / dist_km);
    /* Loop units: the firmware's range_estimate divides the loop peak
     * by K_LOOP=4.096 to recover µV/m, so inject amp = e_peak * K_LOOP
     * to make the round-trip exact. Keep within int16 (~30000). */
    float amp = e_peak * 4.096f;
    if (amp > 28000.0f) amp = 28000.0f;

    float br = bearing * (float)M_PI / 180.0f;
    float ns_gain = cosf(br);
    float ew_gain = sinf(br);

    /* Place the sferic peak ~40 samples before wr so it is inside the
     * detector's 80-sample scan window, with the onset (pre-peak ramp)
     * clear of the 64-sample noise-floor window (wr-144 .. wr-80). */
    int peak_idx = 160;
    int wr       = 200;
    int win_end  = wr;
    /* Fill the whole ring with Gaussian noise first (realistic floor). */
    for (int i = 0; i < RING_LEN; i++) {
        g_ringbuf[i].ch[0] = (int16_t)(rand() % 200 - 100);
        g_ringbuf[i].ch[1] = (int16_t)(rand() % 200 - 100);
        g_ringbuf[i].ch[2] = (int16_t)(rand() % 80 - 40);
        g_ringbuf[i].ch[3] = 0;
    }
    for (int i = peak_idx - 40; i < win_end + 400 && i < RING_LEN; i++) {
        /* t in microseconds; at 8 ksps one sample = 125 us. The *received*
         * sferic (after ionospheric group dispersion) is broadened to
         * ~100–500 us rise + a 1–10 ms slow tail, so use us-scale consts. */
        float t = (float)(i - peak_idx) * (1e6f / ADC_RATE);  /* us */
        float env;
        if (type == CLASS_CG) {
            /* sharp received rise (~200 us) + slow tail (~5 ms) */
            float rise = expf(-t / 200.0f);
            float tail = expf(-t / 8000.0f);
            env = (t < 0) ? 0 : (rise * 0.7f + tail * 0.3f);
        } else {
            /* broader bipolar pulse (~400 us rise, ~1 ms decay) */
            env = (t < 0) ? 0 : expf(-t / 1000.0f) * (1.0f - expf(-t / 400.0f)) * 3.0f;
        }
        float ns = amp * ns_gain * env;
        float ew = amp * ew_gain * env;
        /* Slow-E signature: CG has a large mono-polar slow tail (sign
         * picks the 180° ambiguity); IC has a small bipolar pulse. */
        float es = (type == CLASS_CG)
                 ? amp * 0.5f * expf(-t / 5000.0f) * (t > 0 ? 1 : -1)
                 : amp * 0.15f * expf(-t / 3000.0f) * (t > 0 ? 1 : -1) * 0.3f;
        g_ringbuf[i].ch[0] = (int16_t)ns;
        g_ringbuf[i].ch[1] = (int16_t)ew;
        g_ringbuf[i].ch[2] = (int16_t)es;
        g_ringbuf[i].ch[3] = 0;
    }
    g_ring.wr = wr;
    g_ring.ts_us = 1000000ULL;
}

int main(void)
{
    printf("=== Bolt Compass simulation ===\n");
    ring_reset();
    detect_init();
    classify_init();

    range_model_t model;
    range_defaults(&model);

    struct { float brg, dist; int type; } cases[] = {
        {  45.0f,  50.0f, CLASS_CG },
        { 120.0f, 150.0f, CLASS_CG },
        { 200.0f,  30.0f, CLASS_IC },
        { 310.0f, 200.0f, CLASS_CG },
        {  90.0f,  80.0f, CLASS_IC },
        {   0.0f, 250.0f, CLASS_CG },
    };
    int ncases = (int)(sizeof(cases)/sizeof(cases[0]));
    int ok_brg = 0, ok_type = 0, ok_dist = 0;

    for (int c = 0; c < ncases; c++) {
        ring_reset();
        detect_init();   /* reset debounce + floor between cases */
        inject_sferic(cases[c].brg, cases[c].dist, cases[c].type, &model);

        sferic_t sf;
        int r = detect_sferic(&g_ring, &sf);
        if (!r) {
            printf("case %d: MISS (no detection)\n", c);
            continue;
        }
        classify_t cls;
        classify_sferic(&sf, &cls);
        float brg = bearing_compute(&sf);
        float dist = range_estimate(&sf, &model);

        const char *tn[] = { "CG", "IC", "CC" };
        float brg_err = fabsf(brg - cases[c].brg);
        if (brg_err > 180) brg_err = 360 - brg_err;
        float dist_err = fabsf(dist - cases[c].dist) / cases[c].dist * 100.0f;

        printf("case %d: truth %s brg=%5.0f d=%5.0f | got %s conf=%.2f "
               "brg=%5.1f d=%5.1f | err brg=%.1f° dist=%.0f%%\n",
               c, tn[cases[c].type], cases[c].brg, cases[c].dist,
               tn[cls.label], cls.conf, brg, dist, brg_err, dist_err);

        if (brg_err < 10.0f) ok_brg++;
        if (cls.label == cases[c].type) ok_type++;
        if (dist_err < 50.0f) ok_dist++;
    }

    printf("\nsummary: bearing %d/%d, type %d/%d, distance %d/%d\n",
           ok_brg, ncases, ok_type, ncases, ok_dist, ncases);
    printf("(synthetic weights — real int8 model trained on Blitzortung data)\n");
    return 0;
}