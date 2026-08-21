/* peak.c — Chromatogram peak detection
 *
 * Algorithm:
 *   1. Compute first derivative (central difference) of baseline-corrected signal.
 *   2. Threshold = PLUME_PEAK_DERIV_THRESHOLD_SIGMA * noise_sigma.
 *   3. Peak start: derivative rises above +threshold for ≥3 consecutive samples.
 *   4. Peak end:   derivative falls below -threshold.
 *   5. Apex:       maximum signal within [start, end].
 *   6. Area:       trapezoidal integration of corrected signal over [start, end].
 *   7. Width:      end_time - start_time.
 *   8. Second-derivative check: if d²/dt² at apex is not sufficiently negative,
 *      reject (not a real peak — likely baseline noise).
 */
#include <math.h>
#include <string.h>
#include "esp_log.h"
#include "sdkconfig.h"
#include "peak.h"

static const char *TAG = "peak";

static float central_diff(const tcd_sample_t *s, int i, int n)
{
    if (i <= 0 || i >= n - 1) return 0.0f;
    /* dt in seconds */
    float dt = (s[i + 1].timestamp_us - s[i - 1].timestamp_us) / 1e6f;
    if (dt <= 0) dt = 2.0f / PLUME_TCD_SAMPLE_HZ;
    return (s[i + 1].corrected_uv - s[i - 1].corrected_uv) / dt;
}

static float second_diff(const tcd_sample_t *s, int i, int n)
{
    if (i <= 0 || i >= n - 1) return 0.0f;
    float dt = (s[i + 1].timestamp_us - s[i].timestamp_us) / 1e6f;
    if (dt <= 0) dt = 1.0f / PLUME_TCD_SAMPLE_HZ;
    return (s[i + 1].corrected_uv - 2.0f * s[i].corrected_uv + s[i - 1].corrected_uv) / (dt * dt);
}

int peak_detect(const tcd_sample_t *samples, int n, float noise_sig,
                peak_t *peaks, int max_peaks)
{
    if (n < 5 || noise_sig <= 0) return 0;

    float dthr = PLUME_PEAK_DERIV_THRESHOLD_SIGMA * noise_sig *
                 PLUME_TCD_SAMPLE_HZ;  /* scale to per-sample derivative */
    float min_height = 5.0f * noise_sig;  /* minimum peak height in µV */
    int count = 0;
    int i = 1;

    while (i < n - 1 && count < max_peaks) {
        /* Look for sustained positive derivative → peak start */
        int consec = 0;
        while (i < n - 1) {
            float d = central_diff(samples, i, n);
            if (d > dthr) {
                consec++;
                if (consec >= 3) break;
            } else {
                consec = 0;
            }
            i++;
        }
        if (i >= n - 1 || consec < 3) break;

        int start = i - 2;

        /* Find apex (maximum) and end (derivative goes negative) */
        int apex = start;
        float max_val = samples[start].corrected_uv;
        int end = start;
        int j = start + 1;
        while (j < n - 1) {
            float d = central_diff(samples, j, n);
            if (samples[j].corrected_uv > max_val) {
                max_val = samples[j].corrected_uv;
                apex = j;
            }
            if (d < -dthr && j > apex + 1) {
                /* Sustained negative derivative → end */
                int neg_consec = 1;
                int k = j + 1;
                while (k < n - 1 && neg_consec < 3) {
                    if (central_diff(samples, k, n) < -dthr) neg_consec++;
                    else break;
                    k++;
                }
                if (neg_consec >= 3) {
                    end = j;
                    break;
                }
            }
            j++;
        }
        if (end <= start) end = n - 2;

        /* Validate with second derivative at apex (must be a real maximum) */
        float d2 = second_diff(samples, apex, n);
        float height = max_val - samples[start].corrected_uv;

        if (d2 < 0 && height > min_height) {
            /* Compute area (trapezoidal) */
            float area = 0.0f;
            for (int k = start; k < end; k++) {
                float dt = (samples[k + 1].timestamp_us - samples[k].timestamp_us) / 1e6f;
                area += 0.5f * (samples[k].corrected_uv + samples[k + 1].corrected_uv) * dt;
            }

            /* Retention time relative to run start (sample[0]) */
            float tR = (samples[apex].timestamp_us - samples[0].timestamp_us) / 1e6f;
            float width = (samples[end].timestamp_us - samples[start].timestamp_us) / 1e6f;

            peaks[count].retention_s = tR;
            peaks[count].area_uv_s   = area;
            peaks[count].height_uv   = height;
            peaks[count].width_s     = width;
            peaks[count].start_idx   = start;
            peaks[count].apex_idx    = apex;
            peaks[count].end_idx     = end;
            count++;

            ESP_LOGI(TAG, "Peak %d: tR=%.1fs area=%.0f h=%.0fµV w=%.1fs",
                     count, tR, area, height, width);
        }

        i = end + 1;
    }

    ESP_LOGI(TAG, "Detected %d peaks (noise_sig=%.1fµV)", count, noise_sig);
    return count;
}