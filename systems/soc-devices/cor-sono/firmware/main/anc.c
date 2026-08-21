/*
 * cor-sono / firmware / anc.c
 * Normalized LMS adaptive noise cancellation
 * Removes ambient noise (ref mic) from contact mic signal
 */
#include "main.h"
#include <string.h>

#define N_TAPS   32
static float w[N_TAPS];
static float ref_buf[N_TAPS];

void anc_init(void)
{
    memset(w, 0, sizeof(w));
    memset(ref_buf, 0, sizeof(ref_buf));
}

/* Normalized LMS: ref = ambient, primary = contact
 * Output = contact - filter(ref)  → cleaned body sound
 * Step size mu = 0.01, regularization eps = 1e-6
 */
int16_t anc_process(int16_t contact, int16_t ambient)
{
    /* shift ref buffer */
    for (int i = N_TAPS - 1; i > 0; i--) ref_buf[i] = ref_buf[i - 1];
    ref_buf[0] = (float)ambient;

    /* filter output */
    float y = 0.0f;
    for (int i = 0; i < N_TAPS; i++) y += w[i] * ref_buf[i];

    /* error = desired (contact) - filter output */
    float d = (float)contact;
    float e = d - y;

    /* NLMS weight update */
    float power = 1e-6f;
    for (int i = 0; i < N_TAPS; i++) power += ref_buf[i] * ref_buf[i];
    float mu = 0.01f / power;
    for (int i = 0; i < N_TAPS; i++) w[i] += mu * e * ref_buf[i];

    return (int16_t)e;
}

/* Process a full block; in-place on contact[] */
void anc_process_block(int16_t *contact, const int16_t *ambient, int n)
{
    for (int i = 0; i < n; i++)
        contact[i] = anc_process(contact[i], ambient[i]);
}