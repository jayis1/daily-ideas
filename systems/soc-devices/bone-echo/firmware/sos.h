/*
 * sos.h — Speed of sound: threshold-cross ToF + d/t_f
 */

#ifndef SOS_H
#define SOS_H

#include <stdint.h>

void  sos_init(void);
float sos_compute(const uint16_t *tof_buf, uint32_t n,
                  uint32_t tx_trigger_ts, float d_mm,
                  float probe_delay_us);
float sos_get_last_tof_us(void);

#endif