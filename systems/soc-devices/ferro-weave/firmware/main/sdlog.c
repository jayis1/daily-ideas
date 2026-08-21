/*
 * sdlog.c — SD card CSV + JSON logging (FatFs)
 */
#include "sdlog.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

static char g_fn_csv[32];
static char g_fn_json[32];

int sdlog_mount(void)
{
    /* f_mount(&SDFatFS, "", 1) in firmware. */
    return 0;
}

static void make_filename(char *csv, char *json, size_t n)
{
    /* Use the RTC or a monotonic counter. In sim, time(). */
    static unsigned seq = 0;
    seq++;
    snprintf(csv,  n, "BH_%06u.csv",  seq);
    snprintf(json, n, "BH_%06u.json", seq);
}

int sdlog_write(const sweep_params_t *sp, const geom_t *g,
                const float *H, const float *B, int n,
                const bh_result_t *r)
{
    make_filename(g_fn_csv, g_fn_json, sizeof(g_fn_csv));

    /* ── CSV: header with geometry + params, then H,B columns ──── */
    /* Firmware: f_open + f_printf. Sim: fopen/fprintf on host. */
    FILE *f = fopen(g_fn_csv, "w");
    if (!f) return -1;
    fprintf(f, "# Ferro Weave sweep log\n");
    fprintf(f, "# waveform=%d i_peak=%.3f freq=%.3f ramp=%u hold=%u\n",
            sp->waveform, sp->i_peak, sp->freq,
            sp->ramp_cycles, sp->hold_cycles);
    fprintf(f, "# N1=%u N2=%u l_e=%.4e A2=%.4e A_core=%.4e rho=%.3f\n",
            g->n1, g->n2, g->l_e, g->a2, g->a_core, g->rho);
    fprintf(f, "# B_sat=%.4f H_c=%.2f B_r=%.4f mu_dc=%.1f P_v=%.4f sq=%.3f\n",
            r->b_sat, r->h_c, r->b_r, r->mu_dc, r->p_v, r->squareness);
    fprintf(f, "index,H_A_per_m,B_T\n");
    for (int i = 0; i < n; i++)
        fprintf(f, "%d,%.6f,%.6f\n", i, H[i], B[i]);
    fclose(f);

    /* ── JSON summary ───────────────────────────────────────────── */
    FILE *j = fopen(g_fn_json, "w");
    if (!j) return -1;
    fprintf(j,
        "{\n"
        "  \"device\": \"ferro-weave\",\n"
        "  \"waveform\": %d,\n"
        "  \"i_peak\": %.6f,\n"
        "  \"freq\": %.6f,\n"
        "  \"geometry\": {\"n1\": %u, \"n2\": %u, \"l_e\": %.6e, \"a2\": %.6e, \"a_core\": %.6e, \"rho\": %.3f},\n"
        "  \"result\": {\"b_sat\": %.6f, \"h_c\": %.4f, \"b_r\": %.6f, \"mu_dc\": %.2f, \"mu_inc_peak\": %.2f, \"p_v\": %.6f, \"squareness\": %.4f, \"loop_area\": %.6f, \"n_points\": %d}\n"
        "}\n",
        sp->waveform, sp->i_peak, sp->freq,
        g->n1, g->n2, g->l_e, g->a2, g->a_core, g->rho,
        r->b_sat, r->h_c, r->b_r, r->mu_dc, r->mu_inc_peak,
        r->p_v, r->squareness, r->loop_area, r->n_points);
    fclose(j);
    return 0;
}