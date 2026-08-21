/**
 * spiro_flow/buzzer.h — Coaching buzzer
 */
#ifndef SPIRO_FLOW_BUZZER_H
#define SPIRO_FLOW_BUZZER_H

#include "main.h"

void buzzer_init(void);
void buzzer_set_freq(uint16_t freq_hz, uint8_t duty_pct);
void buzzer_beep(uint16_t freq_hz, uint16_t duration_ms);
void buzzer_coach_start(void);
void buzzer_coach_blast(void);
void buzzer_coach_done(void);

#endif