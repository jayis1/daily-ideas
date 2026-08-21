/*
 * vial_lift.h — NEMA8 stepper for hydrodynamic injection
 */

#ifndef VIAL_LIFT_H
#define VIAL_LIFT_H

/* Initialize vial lift (TIM2 stepper + DRV8833 + PC0/PC1) */
void vial_lift_init(void);

/* Lift inlet vial up by lift_mm */
void vial_lift_up(float lift_mm);

/* Lower vial back down by lift_mm */
void vial_lift_down(float lift_mm);

/* Home the vial lift (find PC5 home switch) */
void vial_lift_home(void);

#endif /* VIAL_LIFT_H */