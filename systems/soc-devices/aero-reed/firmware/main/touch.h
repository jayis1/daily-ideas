/*
 * touch.h — capacitive touch fingering
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define N_PADS 14

typedef enum {
    PAD_OCT_DOWN = 0,   /* T1  */
    PAD_LH1,            /* T2  */
    PAD_LH2,            /* T3  */
    PAD_LH3,            /* T4  */
    PAD_LH4,            /* T5  */
    PAD_LH5,            /* T6  */
    PAD_RH1,            /* T7  */
    PAD_RH2,            /* T8  */
    PAD_RH3,            /* T9  */
    PAD_RH4,            /* T10 */
    PAD_RH5,            /* T11 */
    PAD_OCT_UP,         /* T12 */
    PAD_BEND,           /* T13 */
    PAD_ALT,            /* T14 */
} pad_id_t;

void   touch_init(void);
bool   touch_pad_held(pad_id_t p);
uint32_t touch_pad_mask(void);          /* bitmask of held pads */
int8_t touch_octave_offset(void);       /* -1, 0, +1, +2 */
int16_t touch_decode_note(void);        /* MIDI note or -1 */
void   touch_scan(void);               /* call from sensor task */