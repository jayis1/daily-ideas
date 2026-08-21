/*
 * rtd.c — PT1000 RTD temperature conversion
 *
 * Uses the Callendar-Van Dusen equation for PT1000:
 *   For T >= 0°C:  R(T) = R0*(1 + A*T + B*T²)
 *   For T < 0°C:   R(T) = R0*(1 + A*T + B*T² + C*(T-100)*T³)
 *
 * Inverse (R → T) uses the standard quadratic solution for T >= 0°C
 * and a Newton-Raphson iteration for T < 0°C.
 */

#include "rtd.h"
#include <math.h>

float rtd_temp_to_r(float temp) {
    float t = temp;
    float r;
    if (t >= 0.0f) {
        r = RTD_R0 * (1.0f + RTD_A * t + RTD_B * t * t);
    } else {
        float t3 = t * t * t;
        r = RTD_R0 * (1.0f + RTD_A * t + RTD_B * t * t +
                      RTD_C_NEG * (t - 100.0f) * t3);
    }
    return r;
}

float rtd_r_to_temp(float resistance) {
    if (resistance <= 0.0f) return -273.15f;

    float r_norm = resistance / RTD_R0;

    /* For T >= 0°C (R >= R0): solve quadratic  R/R0 = 1 + AT + BT² */
    if (r_norm >= 1.0f) {
        float a = RTD_B;
        float b = RTD_A;
        float c = 1.0f - r_norm;
        float disc = b * b - 4.0f * a * c;
        if (disc < 0.0f) return -273.15f;
        float t = (-b + sqrtf(disc)) / (2.0f * a);
        return t;
    }

    /* For T < 0°C: Newton-Raphson iteration */
    float t = 0.0f;  /* initial guess */
    for (int i = 0; i < 20; i++) {
        float t3 = t * t * t;
        float f  = 1.0f + RTD_A * t + RTD_B * t * t +
                   RTD_C_NEG * (t - 100.0f) * t3 - r_norm;
        float df = RTD_A + 2.0f * RTD_B * t +
                   RTD_C_NEG * (4.0f * t3 - 300.0f * t * t);
        if (fabsf(df) < 1e-10f) break;
        float dt = -f / df;
        t += dt;
        if (fabsf(dt) < 0.001f) break;  /* 1 mK convergence */
    }
    return t;
}

float rtd_v_to_r(float voltage, float idac_current) {
    if (idac_current <= 0.0f) return 0.0f;
    return voltage / idac_current;
}

float rtd_linearize(float resistance) {
    /* Simple linear approximation for small ranges:
       T ≈ (R - R0) / (R0 * alpha)
       Use this only for quick sanity checks */
    return (resistance - RTD_R0) / (RTD_R0 * RTD_ALPHA);
}