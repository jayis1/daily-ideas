/*
 * cor-sono / firmware / audio.h
 */
#pragma once
#include "main.h"

/* Get latest audio block (contact + ambient, BLOCK_SAMPLES each) */
void audio_get_block(int16_t *contact, int16_t *ambient);

/* Frame counter (increments per 20 ms block) */
uint32_t audio_frame_index(void);