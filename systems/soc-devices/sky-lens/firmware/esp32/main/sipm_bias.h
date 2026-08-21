/* sipm_bias.h — SiPM 30 V bias boost control + monitoring */
#ifndef SIPM_BIAS_H
#define SIPM_BIAS_H
#include <stdbool.h>

void   sipm_bias_init(void);
bool   sipm_bias_enable(void);        /* returns true if rail came up OK */
void   sipm_bias_disable(void);
float  sipm_bias_voltage(void);       /* measured voltage, V */
bool   sipm_bias_fault(void);         /* OCP / thermal fault latched? */
void   sipm_bias_clear_fault(void);

#endif