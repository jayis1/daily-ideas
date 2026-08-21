/**
 * room_modes.h — Room mode detection via narrowband ping-and-listen
 *
 * Sends brief sine tones from 20–300 Hz in 1 Hz steps, measures
 * the decay time after each burst, and flags frequencies where
 * decay is significantly longer than the broadband average.
 */

#ifndef ROOM_MODES_H
#define ROOM_MODES_H

#include <stdint.h>
#include "acoustic_params.h"

/**
 * Play a sequence of narrowband pings from 20 to 300 Hz.
 * Each ping is 50 ms at a single frequency.
 * Called from app_main during MODE_ROOM_MODES measurement.
 *
 * @param sample_rate Sample rate in Hz
 * @return 0 on success
 */
int room_modes_play_pings(uint32_t sample_rate);

/**
 * Analyze captured audio for room mode resonances.
 *
 * Examines the decay characteristics after each ping frequency
 * and identifies room modes where decay time > 2× average.
 *
 * @param captured     Captured audio (int16, left channel)
 * @param num_samples  Number of samples
 * @param sample_rate  Sample rate in Hz
 * @param speed_of_sound Speed of sound in m/s
 * @param results      Output: filled room_modes field
 * @return 0 on success
 */
int room_modes_analyze(const float *ir, uint32_t num_samples,
                        uint32_t sample_rate, float speed_of_sound,
                        acoustic_results_t *results);

#endif /* ROOM_MODES_H */