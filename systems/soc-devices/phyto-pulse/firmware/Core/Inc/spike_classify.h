/*
 * spike_classify.h — int8 1D-CNN spike classifier
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Classifies detected spikes into 3 classes:
 *   0 = Action Potential (AP) — fast, symmetric, 10-100 ms
 *   1 = Variation Potential (VP) — slow, asymmetric, 1-10 s
 *   2 = Artifact — 50/60 Hz mains, motion, electrode pop
 *
 * Uses CMSIS-NN int8 convolution + dense layers.
 */

#ifndef SPIKE_CLASSIFY_H
#define SPIKE_CLASSIFY_H

#include <stdint.h>
#include "spike_detect.h"

/* CNN input size (64 samples, downsampled from event window) */
#define CNN_INPUT_LEN 64

/* 3 output classes */
#define NUM_CLASSES 3

/* Class names */
extern const char *const CLASS_NAMES[NUM_CLASSES];

/* Initialize the classifier (load weights into flash is automatic) */
void spike_classify_init(void);

/* Classify a detected spike event.
 * Extracts a 64-sample window centered on the peak, runs the int8 CNN,
 * and fills in event->classification and event->confidence.
 * Returns classification (0-2) or -1 on error. */
int spike_classify_event(spike_event_t *event);

/* Get the input window used for the last classification (for debug/display) */
void spike_classify_get_last_window(int8_t *buffer, int *actual_len);

#endif /* SPIKE_CLASSIFY_H */