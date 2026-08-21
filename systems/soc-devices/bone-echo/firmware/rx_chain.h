/*
 * rx_chain.h — AD8331 VGA + TGC ramp + BPF control
 */

#ifndef RX_CHAIN_H
#define RX_CHAIN_H

#include <stdint.h>

void rx_chain_init(void);
void rx_chain_set_gain_db(float gain_db);
void rx_chain_set_tgc_ramp(float start_db, float end_db);
float rx_chain_get_gain_db(void);

#endif