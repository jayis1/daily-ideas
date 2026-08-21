/* sd_log.h — microSD chromatogram CSV logging (SPI2) */
#ifndef SD_LOG_H
#define SD_LOG_H

#include "tcd.h"
#include "peak.h"
#include "identify.h"

void sd_init(void);

/* Save a full run: chromatogram CSV + metadata TXT.
 *   samples       — raw TCD samples
 *   n_samples     — count
 *   peaks         — detected peaks
 *   n_peaks       — count
 *   ids           — identifications
 *   sample_vol_ml — sample volume
 *   method_name   — e.g. "M_ETHOS"
 * Returns run number (incremented), or -1 on error. */
int sd_save_run(const tcd_sample_t *samples, int n_samples,
                const peak_t *peaks, int n_peaks,
                const identification_t *ids, int n_ids,
                float sample_vol_ml, const char *method_name,
                float battery_mv, float ambient_temp_c);

/* List runs on card. */
int sd_list_runs(char *out, int max_len);

#endif /* SD_LOG_H */