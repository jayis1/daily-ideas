/*
 * phantom.h — Acrylic phantom reference measurement
 */

#ifndef PHANTOM_H
#define PHANTOM_H

#include <stdint.h>
#include <stdbool.h>

void        phantom_init(void);
bool        phantom_present(void);   /* Reed switch on PB12 */
void        phantom_update_probe_delay(float d_mm, float measured_sos);
float       phantom_get_probe_delay(void);
void        phantom_capture_ref_fft(const uint16_t *buf, uint32_t n);
const float* phantom_get_ref_fft(void);

#endif