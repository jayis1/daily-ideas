/*
 * library.c — 50-material DSC fingerprint library + k-NN matching
 *
 * Features vector: [Tg, Tm, ΔH_melt, Tc, ΔH_cryst]
 * Temperatures in °C, enthalpies in J/g. Missing features = -999.0 (NaN sentinel).
 *
 * Matching: k-NN (k=3) with weighted Euclidean distance in normalized feature space.
 * Each feature is normalized to [0,1] using min-max scaling across the library.
 */

#include "library.h"
#include <math.h>
#include <string.h>

static dsc_entry_t lib[LIBRARY_SIZE] = {
    /* 1-20: Polymers */
    {"LDPE",               {-125, 110, 110, -999, -999}, "Polymer"},
    {"HDPE",               {-120, 135, 210, -999, -999}, "Polymer"},
    {"PP (isotactic)",      {-10, 165, 100,  120,  -95}, "Polymer"},
    {"PS (atactic)",        {100, -999, -999, -999, -999}, "Polymer"},
    {"PET",                 {80, 255, 140, 170,  -35}, "Polymer"},
    {"PA6 (nylon 6)",       {50, 220, 190, 185,  -45}, "Polymer"},
    {"PA66 (nylon 66)",     {60, 265, 250, 215,  -50}, "Polymer"},
    {"PEEK",               {145, 343, 130, 300,  -80}, "Polymer"},
    {"PC (polycarbonate)", {145, -999, -999, -999, -999}, "Polymer"},
    {"PMMA",               {105, -999, -999, -999, -999}, "Polymer"},
    {"PVC (rigid)",        {80, -999, -999, -999, -999}, "Polymer"},
    {"PLA",                {60, 170,  93, 105,  -35}, "Polymer"},
    {"ABS",               {105, -999, -999, -999, -999}, "Polymer"},
    {"SAN",               {115, -999, -999, -999, -999}, "Polymer"},
    {"POM (acetal)",      {-60, 175, 230, 145, -120}, "Polymer"},
    {"PTFE",              {115, 327,  80, 310,  -40}, "Polymer"},
    {"PVDF",              {-35, 177, 105, 140,  -55}, "Polymer"},
    {"EVA (12% VA)",      {-25,  92, 120, -999, -999}, "Polymer"},
    {"TPU",               {-40, 180,  50, -999, -999}, "Polymer"},
    {"Rubber (NR)",       {-70,  30,  20, -999, -999}, "Polymer"},
    /* 21-26: Waxes & fatty acids */
    {"Paraffin wax",      {-999, 58, 210, -999, -999}, "Wax"},
    {"Beeswax",           {-999, 64, 170, -999, -999}, "Wax"},
    {"Carnauba wax",       {-999, 82, 190, -999, -999}, "Wax"},
    {"Microcrystalline", {-999, 72, 150, -999, -999}, "Wax"},
    {"Stearic acid",      {-999, 69, 200, -999, -999}, "Fatty acid"},
    {"Palmitic acid",      {-999, 63, 220, -999, -999}, "Fatty acid"},
    /* 27-31: Metals */
    {"Indium",            {-999, 156.6, 28.7, -999, -999}, "Metal"},
    {"Tin",               {-999, 231.9, 60.2, -999, -999}, "Metal"},
    {"Bismuth",           {-999, 271.4, 53.3, -999, -999}, "Metal"},
    {"Lead",              {-999, 327.5, 23.0, -999, -999}, "Metal"},
    {"Gallium",           {-999, 29.8, 80.1, -999, -999}, "Metal"},
    /* 32-37: Pharmaceuticals */
    {"Ibuprofen",         {-999, 75, 120, -999, -999}, "Pharma"},
    {"Acetaminophen",     {-999, 169, 180, -999, -999}, "Pharma"},
    {"Aspirin",           {-999, 135, 150, -999, -999}, "Pharma"},
    {"Caffeine",          {-999, 235, 110, -999, -999}, "Pharma"},
    {"Sulfathiazole F1",  {-999, 172,  95, -999, -999}, "Pharma"},
    {"Sulfathiazole F2",  {-999, 202,  85, -999, -999}, "Pharma"},
    /* 38-45: Food */
    {"Cocoa butter",      {-999, 34, 110, -999, -999}, "Food"},
    {"Dark chocolate",     {28, 34,  50, -999, -999}, "Food"},
    {"Butter",            {-999, 38,  80, -999, -999}, "Food"},
    {"Coconut oil",       {-999, 24, 100, -999, -999}, "Food"},
    {"Palm oil",          {-999, 36,  90, -999, -999}, "Food"},
    {"Honey (pure)",      {-50, 180,  60, -999, -999}, "Food"},
    {"Sucrose",           {62, 186, -999, -999, -999}, "Food"},
    {"Gelatin",           {210, -999, -999, -999, -999}, "Food"},
    /* 46-50: Resins, chemicals, water */
    {"Epoxy (uncured)",   {-999, 150, 350, -999, -350}, "Resin"},
    {"Epoxy (cured)",     {130, -999, -999, -999, -999}, "Resin"},
    {"Polyester resin",   {70, 150, 200, -999, -200}, "Resin"},
    {"Sulfur (alpha)",    {-999, 115,  60, -999, -999}, "Chemical"},
    {"Water (ice)",       {-999, 0, 334, -999, -999}, "Reference"},
};

/* Feature normalization ranges (min, max) for each of 5 features */
static const float feat_min[NUM_FEATURES] = {
    -125.0f,   /* Tg */
       0.0f,   /* Tm */
      20.0f,   /* ΔH_melt */
    -999.0f,   /* Tc */
    -350.0f,   /* ΔH_cryst */
};
static const float feat_max[NUM_FEATURES] = {
    210.0f,   /* Tg */
   343.0f,   /* Tm */
   350.0f,   /* ΔH_melt */
   310.0f,   /* Tc */
    -20.0f,   /* ΔH_cryst */
};

static float normalize(float val, float min, float max) {
    if (val < -900.0f) return 0.5f;  /* missing feature → neutral */
    float range = max - min;
    if (range <= 0.0f) return 0.0f;
    float n = (val - min) / range;
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return n;
}

void library_init(void) {
    /* Library is statically initialized above. Nothing to do. */
}

const dsc_entry_t *library_get(void) { return lib; }
uint8_t library_get_size(void) { return LIBRARY_SIZE; }

void library_match(const float *unknown_features,
                    dsc_match_t *matches, uint8_t *num_matches) {
    /* Normalize unknown features */
    float unk[NUM_FEATURES];
    for (int f = 0; f < NUM_FEATURES; f++) {
        unk[f] = normalize(unknown_features[f], feat_min[f], feat_max[f]);
    }

    /* Compute distance to all library entries */
    dsc_match_t all_matches[LIBRARY_SIZE];
    for (int i = 0; i < LIBRARY_SIZE; i++) {
        float dist_sq = 0.0f;
        for (int f = 0; f < NUM_FEATURES; f++) {
            float lib_val = normalize(lib[i].features[f], feat_min[f], feat_max[f]);
            float diff = unk[f] - lib_val;
            /* Weight Tm and ΔH_melt more heavily (most diagnostic) */
            float weight = 1.0f;
            if (f == 1) weight = 2.0f;  /* Tm */
            if (f == 2) weight = 1.5f;  /* ΔH_melt */
            dist_sq += weight * diff * diff;
        }
        float dist = sqrtf(dist_sq);

        strncpy(all_matches[i].name, lib[i].name, MAX_NAME_LEN);
        all_matches[i].name[MAX_NAME_LEN-1] = '\0';
        strncpy(all_matches[i].category, lib[i].category, 12);
        all_matches[i].category[11] = '\0';
        all_matches[i].distance = dist;
        all_matches[i].confidence = 0.0f;
    }

    /* Simple insertion sort to find top-3 (k=3) by distance */
    *num_matches = (LIBRARY_SIZE < MAX_MATCHES) ? LIBRARY_SIZE : MAX_MATCHES;
    for (uint8_t k = 0; k < *num_matches; k++) {
        uint8_t best = k;
        for (int i = k + 1; i < LIBRARY_SIZE; i++) {
            if (all_matches[i].distance < all_matches[best].distance) {
                best = (uint8_t)i;
            }
        }
        if (best != k) {
            dsc_match_t tmp = all_matches[k];
            all_matches[k] = all_matches[best];
            all_matches[best] = tmp;
        }
    }

    /* Copy top matches and compute confidence (inverse distance, softmax-like) */
    float total_inv = 0.0f;
    for (uint8_t k = 0; k < *num_matches; k++) {
        matches[k] = all_matches[k];
        total_inv += 1.0f / (matches[k].distance + 0.001f);
    }
    for (uint8_t k = 0; k < *num_matches; k++) {
        matches[k].confidence = (1.0f / (matches[k].distance + 0.001f)) / total_inv;
    }
}