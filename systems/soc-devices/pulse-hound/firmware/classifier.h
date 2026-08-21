/*
 * Pulse Hound — RF Signal Hunter
 * classifier.h — Signal classification interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_CLASSIFIER_H
#define PULSE_HOUND_CLASSIFIER_H

#include "config.h"

signal_class_t classifier_run(void);
signal_class_t classifier_get_current(void);
float classifier_get_confidence(void);
const char *classifier_label(signal_class_t cls);

#endif /* PULSE_HOUND_CLASSIFIER_H */