/*
 * visco-shear / firmware / rheology.h
 * Rheological model fitting (Levenberg-Marquardt) + viscosity computation
 */
#ifndef VISCO_SHEAR_RHEOLOGY_H
#define VISCO_SHEAR_RHEOLOGY_H

#include "main.h"

/* Compute shear rate from angular velocity and spindle geometry */
float rheology_shear_rate(spindle_type_t sp, float omega);

/* Compute shear stress from torque and spindle geometry */
float rheology_torque_to_stress(spindle_type_t sp, float torque_uNm);

/* Fit all models to flow curve, select best by AIC */
void rheology_fit_models(measure_result_t *res);

/* Print model parameters (for debug/UART) */
void rheology_print_fit(const model_fit_t *fit);

#endif