/*
 * patch.h — patch storage (NVS)
 */
#pragma once
#include "synth.h"
#include <stdint.h>

void     patch_load_all(void);
void     patch_save(int idx, const patch_t *p);
patch_t *patch_get(int idx);
const char *patch_name(int idx);
void     patch_select(int idx);
void     patch_next(void);   /* cycle to next patch */
void     patch_prev(void);
int      patch_count(void);  /* always 8 */