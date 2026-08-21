/*
 * visco-shear / firmware / database.h
 * Reference fluid library for identification
 */
#ifndef VISCO_SHEAR_DATABASE_H
#define VISCO_SHEAR_DATABASE_H

int database_init(void);
int database_identify(float viscosity_mPa_s, float temp_c);
const char *database_name(int idx);
int database_count(void);

#endif