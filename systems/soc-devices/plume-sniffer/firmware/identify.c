/* identify.c — Compound identification + concentration estimation
 *
 * Concentration estimate:
 *   The TCD response is approximately linear with mass for each compound.
 *   We use a simple model:  conc_ppm ≈ (area / response_factor) / sample_vol_ml * K
 *   where K is a device-specific calibration constant (default 0.01,
 *   derived from a propane calibration: 1000 ppm·L → 10000 µV·s).
 *   This is a rough estimate; for accurate quantification, run a
 *   calibration standard.
 */
#include <math.h>
#include <string.h>
#include "esp_log.h"
#include "sdkconfig.h"
#include "identify.h"
#include "library.h"

static const char *TAG = "identify";

#define CALIBRATION_K  0.01f   /* ppm·L per µV·s (propane ref) */

int identify_peaks(const peak_t *peaks, int n_peaks, float sample_vol_ml,
                   identification_t *out)
{
    if (sample_vol_ml < 1.0f) sample_vol_ml = 1.0f;  /* avoid div-by-zero */

    for (int i = 0; i < n_peaks; i++) {
        out[i].retention_s  = peaks[i].retention_s;
        out[i].retention_index = library_ri_from_rt(peaks[i].retention_s);
        out[i].area_uv_s    = peaks[i].area_uv_s;
        out[i].height_uv    = peaks[i].height_uv;

        if (out[i].retention_index < 0) {
            out[i].n_matches = 0;
            out[i].est_conc_ppm = 0;
            ESP_LOGW(TAG, "Peak %d: tR=%.1fs out of RI range", i, peaks[i].retention_s);
            continue;
        }

        out[i].n_matches = library_match(out[i].retention_index,
                                         out[i].matches, IDENTIFY_TOP_MATCHES);

        /* Concentration estimate using best match's response factor */
        float rf = 1.0f;
        if (out[i].n_matches > 0) {
            int idx = out[i].matches[0].index;
            const library_entry_t *e = library_get(idx);
            if (e) rf = e->response_factor;
        }
        /* area [µV·s] × K [ppm·L/µV·s] / (vol [mL] / 1000 [mL/L]) / rf */
        out[i].est_conc_ppm = (peaks[i].area_uv_s * CALIBRATION_K) /
                              (sample_vol_ml / 1000.0f) / rf;

        const char *name = out[i].n_matches > 0
            ? library_get(out[i].matches[0].index)->name : "unknown";
        ESP_LOGI(TAG, "Peak %d: tR=%.1fs RI=%.0f → %s (%.0f ppm)",
                 i, peaks[i].retention_s, out[i].retention_index,
                 name, out[i].est_conc_ppm);
    }
    return n_peaks;
}