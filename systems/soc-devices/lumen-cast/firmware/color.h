/**
 * lumen_cast/firmware/color.h — TCS34725 color sensor + CCT/Duv
 */
#ifndef LUMEN_CAST_COLOR_H
#define LUMEN_CAST_COLOR_H

int tcs34725_init(void);
int tcs34725_read_rgbc(uint16_t *r, uint16_t *g, uint16_t *b, uint16_t *c);
void color_compute_cct_duv(uint16_t r, uint16_t g, uint16_t b, uint16_t c,
                            float *cct_k, float *duv, float *x, float *y);

#endif