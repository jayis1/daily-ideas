/*
 * pyro-balance / Core/Inc/balance.h
 * HX711 5g load cell interface — mass acquisition.
 */
#ifndef BALANCE_H
#define BALANCE_H

#include "main.h"

#define BALANCE_MAX_MG   5000.0f   /* 5 g full scale */
#define BALANCE_RES_MG   0.005f    /* 5 µg resolution (after averaging) */
#define BALANCE_RATE_HZ  80

void  balance_init(void);
void  balance_tare(void);
float balance_read_mg(void);       /* blocking single read (averaged over 16) */
float balance_last_mg(void);
float balance_mg_at(uint32_t t_ms); /* from rolling buffer */
void  balance_set_scale(float scale);
void  balance_set_offset(int32_t offset);
float balance_get_scale(void);
int32_t balance_get_offset(void);

#endif /* BALANCE_H */