/*
 * cor-sono / firmware / classifier.h
 */
#pragma once
#include "main.h"

/* Run CNN classifier on an audio block.
 * Returns class_id (0–7). Call classifier_confidence() after. */
int classifier_run(const int16_t *audio, int n);

/* Confidence (0–100) of the last classification */
int classifier_confidence(void);