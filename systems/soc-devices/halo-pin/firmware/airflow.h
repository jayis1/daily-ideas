/*
 * airflow.h — sample-airflow blower control + flow-rate monitor
 *
 * A small brushless blower draws ambient air through a HEPA pre-filter
 * (optional), through the inlet nozzle, past the laser focus region,
 * and out via the exhaust. Flow rate is monitored by a Sensirion
 * SDP810 differential-pressure sensor across a calibrated flow
 * restrictor, providing closed-loop flow control at 1.0 L/min.
 */

#ifndef AIRFLOW_H
#define AIRFLOW_H

#include <stdbool.h>

#define FLOW_TARGET_LPM    1.0f     /* target sample flow */
#define FLOW_MIN_LPM       0.05f   /* below this = fault */
#define FLOW_MAX_LPM       2.0f

void   airflow_init(void);
void   airflow_start(void);
void   airflow_stop(void);
float  airflow_read_lpm(void);     /* current flow rate (L/min) */
bool   airflow_ok(void);

#endif /* AIRFLOW_H */