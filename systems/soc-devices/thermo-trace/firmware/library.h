/*
 * library.h — 50-material DSC fingerprint library + k-NN matching (header)
 */
#ifndef LIBRARY_H
#define LIBRARY_H

#include <stdint.h>

#define LIBRARY_SIZE       50
#define NUM_FEATURES        5   /* Tg, Tm, ΔH_m, Tc, ΔH_c */
#define MAX_MATCHES          3
#define MAX_NAME_LEN        24

typedef struct {
    char  name[MAX_NAME_LEN];
    float features[NUM_FEATURES];  /* [Tg, Tm, ΔH_melt, Tc, ΔH_cryst] */
    char  category[12];             /* "Polymer", "Pharma", etc. */
} dsc_entry_t;

typedef struct {
    char  name[MAX_NAME_LEN];
    char  category[12];
    float distance;
    float confidence;  /* 0.0–1.0 */
} dsc_match_t;

void    library_init(void);
const dsc_entry_t *library_get(void);
void    library_match(const float *unknown_features,
                       dsc_match_t *matches, uint8_t *num_matches);
uint8_t library_get_size(void);

#endif /* LIBRARY_H */