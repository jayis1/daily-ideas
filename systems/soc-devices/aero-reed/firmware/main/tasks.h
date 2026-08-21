/*
 * tasks.h — FreeRTOS task prototypes
 */
#pragma once
#include <stdint.h>

/* Sensor fusion task (100 Hz): reads touch, breath, lip, IMU, updates g_state */
void sensor_task(void *arg);

/* Synth render task: fills I2S DMA buffers */
void synth_task(void *arg);

/* MIDI + display co-task (50 Hz) */
void midi_display_task(void *arg);

/* Power monitor task (1 Hz) */
void power_task(void *arg);

/* BOOT button handler: patch change */
void boot_button_task(void *arg);