/*
 * hall-puck / firmware / Core / Inc / vdp_switch.h
 * Van der Pauw contact switch matrix (2× ADG714)
 *
 * Switch matrix connects 4 sample contacts to I-force+, I-force-,
 * V-sense+, V-sense- buses in any permutation.
 *
 * ADG714 #1 (SW1): switches current path to contacts
 * ADG714 #2 (SW2): switches voltage sense to contacts
 *
 * MIT License.
 */
#ifndef VDP_SWITCH_H
#define VDP_SWITCH_H

#include <stdint.h>
#include <stdbool.h>

/* Contact identifiers */
#define CONTACT_1   0
#define CONTACT_2   1
#define CONTACT_3   2
#define CONTACT_4   3

/* Measurement configurations */
typedef enum {
    /* Van der Pauw resistances */
    VDP_RA_FWD = 0,     /* I: 1→2, V: 3→4 */
    VDP_RA_REV,         /* I: 2→1, V: 4→3 */
    VDP_RB_FWD,         /* I: 2→3, V: 4→1 */
    VDP_RB_REV,         /* I: 3→2, V: 1→4 */
    /* Hall effect */
    HALL_BP_FWD,        /* I: 1→3, V: 2→4, B+ */
    HALL_BP_REV,        /* I: 3→1, V: 4→2, B+ */
    HALL_BM_FWD,        /* I: 1→3, V: 2→4, B- */
    HALL_BM_REV,        /* I: 3→1, V: 4→2, B- */
    /* Contact check */
    CONTACT_CHECK_1,    /* I: 1→2, V: 3→4 (check impedance) */
    CONTACT_CHECK_2,    /* I: 2→3, V: 4→1 */
    CONTACT_CHECK_3,    /* I: 3→4, V: 1→2 */
    CONTACT_CHECK_4,    /* I: 4→1, V: 2→3 */
    /* Short (for zero calibration) */
    SHORT_ZERO,         /* V+ and V- both to contact 1 */
    SWITCH_OFF,         /* All switches open */
} vdp_config_t;

/* Initialize switch matrix (SPI GPIO) */
void vdp_switch_init(void);

/* Set measurement configuration (routes contacts) */
void vdp_switch_set_config(vdp_config_t config);

/* Open all switches */
void vdp_switch_all_open(void);

/* Check if a contact has valid connection (impedance < threshold) */
bool vdp_switch_check_contact(int contact);

/* Get configuration name string */
const char *vdp_switch_config_name(vdp_config_t config);

#endif /* VDP_SWITCH_H */