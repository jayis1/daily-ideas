/*
 * tx_pulser.h — HRTIM-triggered 200 V 1 MHz 5-cycle TX burst
 */

#ifndef TX_PULSER_H
#define TX_PULSER_H

#include <stdint.h>
#include <stdbool.h>

void     tx_pulser_init(void);
void     tx_pulser_arm(void);        /* Enable HV charge pump, charge to 200 V */
void     tx_pulser_disarm(void);     /* Discharge HV to GND via 100k bleeder */
bool     tx_pulser_armed(void);
bool     tx_pulser_hv_ok(void);      /* HV within 180–220 V? */
void     tx_pulser_fire(void);       /* HRTIM edge → 5-cycle 1 MHz burst */
uint32_t tx_pulser_get_trigger_ts(void); /* HRTIM counter at fire */

#endif