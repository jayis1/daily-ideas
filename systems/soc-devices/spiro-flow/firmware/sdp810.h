/**
 * spiro_flow/sdp810.h — SDP810 differential pressure sensor
 */
#ifndef SPIRO_FLOW_SDP810_H
#define SPIRO_FLOW_SDP810_H

#include "main.h"

int sdp810_init(void);
int sdp810_start_continuous(void);
int sdp810_stop_continuous(void);
int sdp810_read_pressure(float *diff_pa, float *temp_c);

#endif