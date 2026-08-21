/**
 * cordic_math.h — CORDIC-accelerated sin/cos/sqrt wrappers
 *
 * The STM32G474 has a hardware CORDIC coprocessor that computes
 * sin, cos, sqrt, arctan, etc. in a few cycles. These wrappers
 * provide a clean interface with double-precision fallback.
 */
#ifndef CORDIC_MATH_H
#define CORDIC_MATH_H

double cordic_sin(double rad);
double cordic_cos(double rad);
double cordic_sqrt(double x);

#endif /* CORDIC_MATH_H */