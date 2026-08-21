/* mux.h — ADG715 8:1 analog switch driver for electrode selection
 *
 * The ADG715 connects one of 5 working electrodes to the AD5941's
 * working electrode (WE) input. Selection is via 3 address pins (S0-S2).
 */

#ifndef TASTE_BEAD_MUX_H
#define TASTE_BEAD_MUX_H

#include "esp_err.h"

/* Electrode IDs */
#define MUX_ELECTRODE_AU    0   /* Gold */
#define MUX_ELECTRODE_PT    1   /* Platinum */
#define MUX_ELECTRODE_AG    2   /* Silver/Silver Chloride */
#define MUX_ELECTRODE_GC    3   /* Glassy Carbon */
#define MUX_ELECTRODE_CU    4   /* Copper */
#define MUX_ELECTRODE_NONE  7   /* Disconnected (safe default) */

/* Initialize mux GPIO pins */
esp_err_t mux_init(int en_pin, int s0_pin, int s1_pin, int s2_pin);

/* Select an electrode (0-4) or disconnect (7) */
esp_err_t mux_select(int electrode);

/* Disable the mux (disconnect all electrodes) */
esp_err_t mux_disable(void);

/* Get currently selected electrode */
int mux_get_selected(void);

#endif /* TASTE_BEAD_MUX_H */