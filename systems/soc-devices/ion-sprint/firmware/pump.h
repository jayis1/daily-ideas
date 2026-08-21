/*
 * pump.h — Peristaltic flush pump control
 */

#ifndef PUMP_H
#define PUMP_H

/* Initialize pump (TIM4 PWM + PB9 direction) */
void pump_init(void);

/* Run pump for flush_time_s at PUMP_DUTY_FLUSH duty */
void pump_flush(uint32_t flush_time_s);

/* Stop pump */
void pump_off(void);

#endif /* PUMP_H */