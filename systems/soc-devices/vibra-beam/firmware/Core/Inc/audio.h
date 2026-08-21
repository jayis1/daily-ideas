/*
 * audio.h — heterodyne-to-audio (I2S MAX98357A)
 */

#ifndef AUDIO_H
#define AUDIO_H

#include <stdint.h>

void audio_init(void);
void audio_start(void);
void audio_stop(void);
void audio_set_gain(float g);
void audio_set_shift(float s);
/* Push a velocity (mm/s) sample; audio thread translates to audible */
void audio_push_velocity(float vel_mms);

#endif /* AUDIO_H */