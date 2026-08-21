/*
 * Hive Mind — Acoustic Analyzer Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef ACOUSTIC_ANALYZER_H
#define ACOUSTIC_ANALYZER_H

typedef enum {
    AC_QUEENRIGHT = 0,
    AC_QUEENLESS,
    AC_SWARMING,
    AC_FANNING,
    AC_PIPING,
    AC_ROBBING,
    AC_CLUSTERING,
    AC_DEAD,
    AC_MAX
} acoustic_class_t;

typedef struct {
    acoustic_class_t cls;
    uint16_t dominant_freq_hz;
} acoustic_result_t;

void acoustic_analyzer_init(void);
acoustic_result_t acoustic_analyzer_classify(void);
const char *acoustic_class_name(acoustic_class_t cls);

#endif /* ACOUSTIC_ANALYZER_H */