/* library.c — Kovats retention-index compound library (40 entries)
 *
 * RI values are for a non-polar 5% OV-101 column (dimethylsilicone),
 * which is close to the DB-1 / HP-1 / OV-1 family. Values are from
 * standard GC reference tables (NIST WebBook, SDBS) scaled to the
 * n-alkane Kovats system.
 */
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "library.h"

static const char *TAG = "library";

/* n-alkane anchors: C5(500) C6(600) C7(700) C8(800) C9(900) C10(1000)
 * C11(1100) C12(1200) C13(1300) C14(1400) C15(1500) C16(1600)
 * Default retention times (s) for the default method — user must calibrate.
 * Index 0=C5 ... 11=C16 */
#define N_ALKANES 12
static float s_anchor_rt[N_ALKANES] = {
    30, 48, 72, 105, 145, 195, 255, 325, 405, 495, 595, 705
};
static const int s_anchor_ri[N_ALKANES] = { 500,600,700,800,900,1000,1100,1200,1300,1400,1500,1600 };

/* ---- Compound library ---- */
static const library_entry_t s_library[] = {
    {"Freon-134a",       220,  420,   0.35f},
    {"Formaldehyde",     320,  500,   0.60f},
    {"Methanol",         340,  675,   0.55f},
    {"Propane",          300,  749,   1.00f},
    {"Acetaldehyde",     410,  750,   0.65f},
    {"Butane",           400,  106,   0.90f},
    {"Diethyl ether",    450,  602,   0.80f},
    {"Trimethylamine",   450,  756,   0.70f},
    {"Pentane",          500,  109,   0.85f},
    {"Acetone",          490,  676,   0.50f},
    {"Isoprene",         500,  787,   0.75f},
    {"Ethanol",          510,  641,   0.45f},
    {"Isopropanol",      540,  676,   0.42f},
    {"1-Propanol",       545,  712,   0.40f},
    {"Ethyl acetate",    610,  141,   0.55f},
    {"Acetic acid",      620,  641,   0.38f},
    {"Dichloromethane",  640,  750,   0.72f},
    {"Chloroform",       570,  671,   0.78f},
    {"Hexane",           600,  110,   0.80f},
    {"MEK (2-butanone)", 575,  789,   0.48f},
    {"Cyclohexane",      690,  110,   0.75f},
    {"Benzene",          650,  714,   0.82f},
    {"1-Butanol",        660,  713,   0.35f},
    {"Heptane",          700,  142,   0.78f},
    {"Pyridine",         750,  110,   0.45f},
    {"Toluene",          760,  108,   0.80f},
    {"Dimethyl disulfide",740, 624,   0.60f},
    {"Ethylbenzene",     850,  100,   0.75f},
    {"m-Xylene",         870,  108,   0.73f},
    {"o-Xylene",         880,  954,   0.73f},
    {"Styrene",          890,  100,   0.70f},
    {"Hexanal",          800,  662,   0.50f},
    {"Butyric acid",     790,  107,   0.32f},
    {"Nonane",           900,  428,   0.70f},
    {"alpha-Pinene",     940,  806,   0.68f},
    {"1-Octen-3-ol",     980,  339,   0.40f},
    {"Decane",          1000,  124,   0.68f},
    {"Limonene",        1030,  598,   0.65f},
    {"Nonanal",         1100,  124,   0.55f},
    {"Naphthalene",     1180,  912,   0.62f},
};
static const int s_library_count = sizeof(s_library) / sizeof(s_library[0]);

const library_entry_t *library_get_all(int *count)
{
    if (count) *count = s_library_count;
    return s_library;
}

const library_entry_t *library_get(int index)
{
    if (index < 0 || index >= s_library_count) return NULL;
    return &s_library[index];
}

int library_match(float ri, library_match_t *out, int max_out)
{
    /* Simple nearest-N by |ΔRI| */
    int n = s_library_count < 64 ? s_library_count : 64;
    float deltas[64];
    int   idx[64];
    for (int i = 0; i < n; i++) {
        deltas[i] = fabsf(ri - (float)s_library[i].retention_index);
        idx[i] = i;
    }
    /* Insertion sort (small N) */
    for (int i = 1; i < n; i++) {
        float d = deltas[i]; int id_ = idx[i]; int j = i - 1;
        while (j >= 0 && deltas[j] > d) { deltas[j+1] = deltas[j]; idx[j+1] = idx[j]; j--; }
        deltas[j+1] = d; idx[j+1] = id_;
    }
    int result = 0;
    for (int i = 0; i < max_out && i < n; i++) {
        if (deltas[i] > 30.0f) break;   /* too far to be a match */
        out[result].index = idx[i];
        out[result].delta_ri = deltas[i];
        result++;
    }
    return result;
}

float library_ri_from_rt(float retention_s)
{
    /* Find bracketing alkanes and linearly interpolate RI */
    if (retention_s <= s_anchor_rt[0]) return -1.0f;
    if (retention_s >= s_anchor_rt[N_ALKANES - 1]) return -1.0f;

    for (int i = 0; i < N_ALKANES - 1; i++) {
        if (retention_s >= s_anchor_rt[i] && retention_s <= s_anchor_rt[i + 1]) {
            float frac = (retention_s - s_anchor_rt[i]) /
                         (s_anchor_rt[i + 1] - s_anchor_rt[i]);
            return (float)s_anchor_ri[i] + frac * (float)(s_anchor_ri[i + 1] - s_anchor_ri[i]);
        }
    }
    return -1.0f;
}

bool library_set_anchors(const float *rt_alkanes, int n)
{
    if (n > N_ALKANES) n = N_ALKANES;
    memcpy(s_anchor_rt, rt_alkanes, n * sizeof(float));

    nvs_handle_t h;
    if (nvs_open("plume", NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_blob(h, "alk_anchors", s_anchor_rt, sizeof(s_anchor_rt));
        nvs_commit(h);
        nvs_close(h);
        ESP_LOGI(TAG, "Anchors saved to NVS");
        return true;
    }
    ESP_LOGW(TAG, "NVS save failed, anchors in RAM only");
    return false;
}

int library_get_anchors(float *rt_alkanes, int max_n)
{
    /* Try loading from NVS first */
    nvs_handle_t h;
    if (nvs_open("plume", NVS_READONLY, &h) == ESP_OK) {
        size_t len = sizeof(s_anchor_rt);
        if (nvs_get_blob(h, "alk_anchors", s_anchor_rt, &len) == ESP_OK) {
            ESP_LOGI(TAG, "Anchors loaded from NVS");
        }
        nvs_close(h);
    }
    int n = N_ALKANES < max_n ? N_ALKANES : max_n;
    memcpy(rt_alkanes, s_anchor_rt, n * sizeof(float));
    return n;
}