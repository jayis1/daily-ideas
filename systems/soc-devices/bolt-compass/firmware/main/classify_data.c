/*
 * classify_data.c — int8 classifier weights (synthetic, illustrative)
 *
 * The real weights are trained offline on ~50 000 labeled sferics from
 * the Blitzortung / LOFAR public archives (see scripts/train_classifier.py)
 * and quantized to int8. Here we provide a hand-tuned proxy that captures
 * the known discriminative signs:
 *
 *   CG : large slow_tail_ratio (>0.3), sharp rise (<8 us), e_sign != 0,
 *        high loop_coherence, low-ish centroid (~6-9 kHz).
 *   IC : low slow_tail_ratio (<0.15), broader rise (>12 us),
 *        e_sign often 0, lower coherence, higher centroid.
 *   CC : very low slow_tail_ratio, very broad, near-zero e_sign,
 *        lowest coherence.
 *
 /* Weight matrix W[NCLASS][NFEAT] in int8 (scale 1/64), bias[NCLASS] int8
  * (scale 1/16).  Features are normalized to roughly [-8,+8] (see detect.c).
  * logits = W·feat + bias, then softmax.
  */
 #include "classify.h"
 #include <math.h>

 static const int8_t W[NCLASS][NFEAT] = {
     /* CG  — rewards high slow_tail(f6,f13), sharp rise(low f4), strong
      * E sign(f9), high coherence(f7,f14), high zc/rise ratio(f11) */
     {  0,   0,  10,   0,  -20,  12,  28,  16,  -6,  20,   8,  20,   0,  20,  16,  -4 },
     /* IC  — rewards moderate rise(f4), low-ish slow tail(neg f6),
      * weak E sign(neg f9), lower coherence(neg f7), high centroid(f8),
      * high peak amplitude(f10) to distinguish from weak CC */
     {  0,   0,  -2,   0,   12,   6,  -8,  -4,  16,  -8,  16,   0,   0,  -8,  -4,  12 },
     /* CC  — rewards very low slow tail(very neg f6), very broad(high f4),
      * zero E sign(neg f9), low coherence(neg f7), LOW amplitude(neg f10) */
     {  0,   0,  -8,   0,   24,   4, -24, -16,   6, -16, -16,  -8,   0, -20, -16,   2 },
 };

 static const int8_t bias[NCLASS] = { 4, 2, -4 };

void classify_init(void) { /* nothing — weights are const */ }

void classify_sferic(const sferic_t *s, classify_t *out)
{
    float logits[NCLASS];
    for (int c = 0; c < NCLASS; c++) {
        int32_t acc = (int32_t)bias[c] << 4;   /* bias scale 1/16 */
        for (int f = 0; f < NFEAT; f++) {
            /* feat already roughly in int8-ish range; scale by 1 to keep int */
            float fv = s->feat[f];
            int32_t q = (int32_t)(fv * 4.0f);   /* bring into int8 range */
            if (q >  127) q =  127;
            if (q < -128) q = -128;
            acc += (int32_t)W[c][f] * q;
        }
        logits[c] = (float)acc / (64.0f * 4.0f); /* undo W (1/64) and q (x4) */
    }
    /* softmax */
    float mx = logits[0];
    for (int c = 1; c < NCLASS; c++) if (logits[c] > mx) mx = logits[c];
    float sum = 0;
    for (int c = 0; c < NCLASS; c++) {
        out->prob[c] = expf(logits[c] - mx);
        sum += out->prob[c];
    }
    int best = 0;
    for (int c = 0; c < NCLASS; c++) {
        out->prob[c] /= sum;
        if (out->prob[c] > out->prob[best]) best = c;
    }
    out->label = best;
    out->conf  = out->prob[best];
}