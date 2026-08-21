/*
 * Pulse Hound — RF Signal Hunter
 * audio.h — Audio feedback interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_AUDIO_H
#define PULSE_HOUND_AUDIO_H

void audio_init(void);
void audio_update(float rssi_dbm);
void audio_enable(void);
void audio_disable(void);
void audio_mute(void);
void audio_unmute(void);
int  audio_is_enabled(void);
float audio_get_click_rate(void);

#endif /* PULSE_HOUND_AUDIO_H */