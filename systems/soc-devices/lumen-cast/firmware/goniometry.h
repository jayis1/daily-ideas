/**
 * lumen_cast/firmware/goniometry.h — Photometric computation
 */
#ifndef LUMEN_CAST_GONIOMETRY_H
#define LUMEN_CAST_GONIOMETRY_H

void goniometry_compute(scan_buffer_t *s, photo_result_t *r);
float goniometry_integrate_flux(const scan_buffer_t *s);
float goniometry_beam_angle(const scan_buffer_t *s, float fraction);
void goniometry_find_peak(const scan_buffer_t *s, float *peak_cd,
                           float *az, float *el);

#endif