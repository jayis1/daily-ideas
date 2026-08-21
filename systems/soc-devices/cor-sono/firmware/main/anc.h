/*
 * cor-sono / firmware / anc.h
 */
#pragma once
#include "main.h"

/* Process a single sample pair; returns cleaned contact signal */
int16_t anc_process(int16_t contact, int16_t ambient);

/* Process a full block in-place on contact[] */
void anc_process_block(int16_t *contact, const int16_t *ambient, int n);