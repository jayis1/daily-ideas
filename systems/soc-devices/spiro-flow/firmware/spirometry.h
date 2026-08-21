/**
 * spiro_flow/spirometry.h — Spirometry computation header
 */
#ifndef SPIRO_FLOW_SPIROMETRY_H
#define SPIRO_FLOW_SPIROMETRY_H

#include "main.h"

void spirometry_compute(maneuver_buffer_t *m, const patient_t *p,
                         const float *ambient, spiro_result_t *r);
float compute_btps(float temp_c, float pressure_mmhg, float humidity_pct);
void compute_predicted(const patient_t *p, float *fev1_pred, float *fvc_pred,
                        float *fev1_fvc_pred, float *lln_ratio);
quality_grade_t grade_maneuver(const maneuver_buffer_t *m, const spiro_result_t *r);

#endif