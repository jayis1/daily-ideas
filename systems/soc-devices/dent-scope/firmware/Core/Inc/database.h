/*
 * dent-scope / Core/Inc/database.h
 * Dent Scope — 30-material hardness/modulus library + k-NN matching
 * MIT License.
 */
#ifndef DATABASE_H
#define DATABASE_H

#include "main.h"

void database_init(void);
void database_match(ds_status_t *st);
const char *database_name(int idx);

#endif /* DATABASE_H */