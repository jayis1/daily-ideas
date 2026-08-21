/*
 * cordic_math.h — CORDIC-accelerated math for STM32G491
 *
 * The STM32G491 has a hardware CORDIC coprocessor that can
 * compute sin, cos, atan2, magnitude, and phase much faster
 * than software floating-point. This module wraps the HAL CORDIC
 * interface for use in admittance circle fitting and FFT.
 */

#ifndef QUARTZ_TUNER_CORDIC_MATH_H
#define QUARTZ_TUNER_CORDIC_MATH_H

#include <math.h>

/* CORDIC-accelerated trig functions */
float cordic_sin(float x);
float cordic_cos(float x);
float cordic_atan2(float y, float x);
float cordic_magnitude(float re, float im);
float cordic_phase(float re, float im);

#endif