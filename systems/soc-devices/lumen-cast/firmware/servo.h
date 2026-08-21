/**
 * lumen_cast/firmware/servo.h — SG90 servo control
 */
#ifndef LUMEN_CAST_SERVO_H
#define LUMEN_CAST_SERVO_H

void servo_init(void);
void servo_set_elevation(float elev_deg);

#endif