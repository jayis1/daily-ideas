/*
 * patient.h — Patient ID + age + sex + ethnicity input
 */

#ifndef PATIENT_H
#define PATIENT_H

#include <stdint.h>
#include <stdbool.h>

void   patient_init(void);
void   patient_start_entry(void);
void   patient_poll_input(void);
bool   patient_entry_complete(void);

uint16_t patient_get_id(void);
void     patient_set_id(uint16_t id);
uint8_t  patient_get_age(void);
void     patient_set_age(uint8_t age);
uint8_t  patient_get_sex(void);        /* 0=male, 1=female */
void     patient_set_sex(uint8_t sex);
uint8_t  patient_get_ethnicity(void);  /* 0-3 */
void     patient_set_ethnicity(uint8_t eth);
bool     patient_has_prior_fracture(void);

#endif