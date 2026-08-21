/*
 * library.h — Specific rotation compound library
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Stores [α]_D (specific rotation at 589nm, 20°C), temperature coefficient,
 * and Drude parameters for up to 50 reference compounds. Supports k-NN
 * matching against measured rotation and Drude parameters.
 */
#ifndef LIBRARY_H
#define LIBRARY_H

#include <stdint.h>
#include <stdbool.h>
#include "drude.h"

#define LIBRARY_MAX_COMPOUNDS 50
#define LIBRARY_MAX_CUSTOM    10
#define LIBRARY_NAME_MAX_LEN   24

typedef struct {
    char    name[LIBRARY_NAME_MAX_LEN];
    double  specific_rotation;   /* [α]_D at 20°C, 589nm, deg·mL/(g·dm) */
    double  temp_coefficient;   /* d[α]/dT per °C (dimensionless factor) */
    double  drude_K;             /* Drude strength constant */
    double  drude_lambda0;       /* Drude absorption wavelength (nm) */
    uint8_t is_custom;           /* 1 = user-added, 0 = built-in */
} library_entry_t;

void library_init(void);
int  library_size(void);
const library_entry_t *library_get(int index);
int  library_find_by_name(const char *name);

/* Add a custom compound (returns index, or -1 if full) */
int  library_add(const char *name, double alpha_d, double temp_coeff,
                 double K, double lambda0);

/* Remove a custom compound */
int  library_remove(int index);

/* Match measured rotation + Drude params against library (k-NN) */
typedef struct {
    int    best_index;
    double confidence;       /* 0-100% */
    double distance;         /* Euclidean distance to best match */
} library_match_t;

library_match_t library_match(double alpha_589, double alpha_405,
                               double alpha_520, const drude_result_t *drude);

/* Save/load custom entries to SD card */
void library_load_from_sd(void);
void library_save_to_sd(void);

#endif /* LIBRARY_H */