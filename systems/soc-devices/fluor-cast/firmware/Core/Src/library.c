/*
 * library.c — 50-compound fluorescence library and k-NN classifier
 *
 * The library stores 48-dimensional feature vectors for each compound.
 * k-NN classification finds the 5 nearest neighbors in feature space.
 * Per-feature inverse-variance weighting is applied to the distance metric.
 */

#include "library.h"
#include "main.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

/* ── Default Library (50 compounds) ──────────────────── */
/* Feature vectors are simplified prototypes.
 * In production, these would be measured from actual standards
 * and stored in external SPI flash (W25Q128).
 * Each entry: name, category, ex_peak, em_peak, 48 features, calibration */

static library_entry_t default_library[LIBRARY_SIZE] = {
    /* 0: Tryptophan */
    {"Tryptophan", "Amino acid", 280, 350,
     {0,0,0, 0,500,0, 0,0,0, 350,25,0,0,0,0,0,0,0, 350,280,5000,0.05,25000,340,420,0.02,
      120,0.3,1.2,0.8,0.9,1.1,0.5,0.001, 500,1.2,2.0,500,5.0,0.0,500,350,0},
     0.002f, 0.1f, 0.999f},

    /* 1: Tyrosine */
    {"Tyrosine", "Amino acid", 275, 305,
     {0,300,0, 0,100,0, 0,0,0, 305,260,3000,0.03,15000,310,305,0.04,
      80,0.2,0.9,0.6,0.8,1.0,0.3,0.002, 300,0.8,1.5,300,3.0,0.0,300,305,0},
     0.003f, 0.2f, 0.998f},

    /* 2: Phenylalanine */
    {"Phenylalanine", "Amino acid", 260, 282,
     {200,0,0, 0,0,0, 0,0,0, 282,255,2000,0.02,8000,282,260,0.03,
      50,0.1,0.7,0.4,0.7,0.9,0.2,0.003, 200,0.5,1.0,200,2.0,0.0,200,282,0},
     0.005f, 0.3f, 0.995f},

    /* 3: NADH */
    {"NADH", "Cofactor", 340, 460,
     {0,0,0, 0,0,0, 0,0,0, 460,335,8000,0.08,40000,460,340,0.15,
      300,0.5,1.5,1.0,1.2,1.3,0.7,0.001, 800,2.0,3.0,800,8.0,0.0,800,460,0},
     0.001f, 0.05f, 0.999f},

    /* 4: FAD */
    {"FAD", "Cofactor", 450, 525,
     {0,0,0, 0,0,0, 0,0,200, 525,440,6000,0.06,30000,525,450,0.10,
      200,0.4,1.3,0.8,1.0,1.2,0.5,0.002, 600,1.5,2.5,600,6.0,0.0,600,525,0},
     0.002f, 0.1f, 0.997f},

    /* 5: Riboflavin (B2) */
    {"Riboflavin", "Vitamin", 440, 530,
     {0,0,0, 0,0,0, 0,0,500, 530,435,7000,0.07,35000,530,440,0.12,
      250,0.4,1.4,0.9,1.1,1.3,0.6,0.001, 700,1.8,2.8,700,7.0,0.0,700,530,0},
     0.0015f, 0.08f, 0.998f},

    /* 6: Thiamine (B1) */
    {"Thiamine", "Vitamin", 365, 440,
     {0,0,0, 0,400,0, 0,0,0, 440,365,5000,0.05,25000,440,365,0.08,
      150,0.3,1.1,0.7,0.9,1.1,0.4,0.002, 400,1.0,2.0,400,4.0,0.0,400,440,0},
     0.002f, 0.15f, 0.996f},

    /* 7: Pyridoxine (B6) */
    {"Pyridoxine", "Vitamin", 320, 390,
     {0,0,0, 0,300,0, 0,0,0, 390,310,3500,0.04,18000,390,340,0.06,
      100,0.2,1.0,0.5,0.8,1.0,0.3,0.003, 350,0.8,1.5,350,3.5,0.0,350,390,0},
     0.003f, 0.2f, 0.994f},

    /* 8: Chlorophyll-a */
    {"Chlorophyll-a", "Pigment", 440, 680,
     {0,0,0, 0,0,0, 0,0,8000, 680,440,9000,0.09,45000,680,440,0.20,
      400,0.6,1.6,1.1,1.3,1.4,0.8,0.001, 900,2.5,3.5,900,9.0,0.0,900,680,0},
     0.0008f, 0.02f, 0.999f},

    /* 9: Chlorophyll-b */
    {"Chlorophyll-b", "Pigment", 470, 660,
     {0,0,0, 0,0,0, 0,0,6000, 660,465,7500,0.07,38000,660,470,0.15,
      300,0.5,1.4,0.9,1.1,1.3,0.6,0.002, 750,2.0,3.0,750,7.5,0.0,750,660,0},
     0.001f, 0.05f, 0.998f},

    /* 10: Phycocyanin */
    {"Phycocyanin", "Pigment", 620, 650,
     {0,0,0, 0,0,0, 0,0,5000, 650,615,6000,0.06,30000,650,525,0.10,
      200,0.4,1.2,0.7,0.9,1.1,0.4,0.002, 500,1.2,2.0,500,5.0,0.0,500,650,0},
     0.002f, 0.1f, 0.995f},

    /* 11: Fluorescein */
    {"Fluorescein", "Tracer dye", 470, 520,
     {0,0,0, 0,0,0, 0,0,10000, 520,470,15000,0.15,75000,520,470,0.25,
      600,0.8,2.0,1.5,1.5,1.5,1.0,0.001, 1500,3.0,4.0,1500,15.0,0.0,1500,520,0},
     0.0001f, 0.001f, 0.9999f},

    /* 12: Rhodamine B */
    {"Rhodamine B", "Tracer dye", 525, 580,
     {0,0,0, 0,0,0, 0,0,9000, 580,525,12000,0.12,60000,580,525,0.20,
      400,0.6,1.5,1.0,1.2,1.4,0.7,0.001, 1200,2.5,3.5,1200,12.0,0.0,1200,580,0},
     0.0002f, 0.002f, 0.999f},

    /* 13: Rhodamine 6G */
    {"Rhodamine 6G", "Tracer dye", 525, 560,
     {0,0,0, 0,0,0, 0,0,8500, 560,525,11000,0.11,55000,560,525,0.18,
      350,0.5,1.4,0.9,1.1,1.3,0.6,0.001, 1100,2.2,3.2,1100,11.0,0.0,1100,560,0},
     0.0002f, 0.003f, 0.999f},

    /* 14: Quinine sulfate */
    {"Quinine sulfate", "Standard", 350, 455,
     {0,0,0, 0,8000,0, 0,0,0, 455,350,10000,0.10,50000,455,350,0.16,
      500,0.7,1.8,1.2,1.4,1.5,0.9,0.001, 1000,2.0,3.0,1000,10.0,0.0,1000,455,0},
     0.0001f, 0.001f, 0.9999f},

    /* 15: Esculin */
    {"Esculin", "Coumarin", 365, 460,
     {0,0,0, 0,6000,0, 0,0,0, 460,365,7000,0.07,35000,460,365,0.11,
      200,0.4,1.3,0.8,1.0,1.2,0.5,0.002, 700,1.5,2.5,700,7.0,0.0,700,460,0},
     0.002f, 0.1f, 0.997f},

    /* 16: Umbelliferone */
    {"Umbelliferone", "Coumarin", 365, 455,
     {0,0,0, 0,5500,0, 0,0,0, 455,365,6500,0.06,32000,455,365,0.10,
      180,0.3,1.2,0.7,0.9,1.1,0.4,0.002, 650,1.2,2.2,650,6.5,0.0,650,455,0},
     0.002f, 0.12f, 0.996f},

    /* 17: 4-Methylumbelliferone */
    {"4-Methylumbelliferone", "Coumarin", 365, 445,
     {0,0,0, 0,5000,0, 0,0,0, 445,365,5500,0.05,28000,445,365,0.09,
      150,0.3,1.1,0.6,0.8,1.0,0.3,0.003, 550,1.0,1.8,550,5.5,0.0,550,445,0},
     0.0025f, 0.15f, 0.995f},

    /* 18: Humic acid (Suwannee) */
    {"Humic acid", "DOM", 320, 420,
     {0,0,0, 0,3500,0, 0,500,0, 420,320,4000,0.04,20000,420,340,0.07,
      120,0.2,0.9,0.5,0.7,0.9,0.2,0.003, 400,0.8,1.5,400,4.0,0.0,400,420,0},
     0.005f, 0.5f, 0.99f},

    /* 19: Fulvic acid (Suwannee) */
    {"Fulvic acid", "DOM", 320, 400,
     {0,0,0, 0,3000,0, 0,400,0, 400,320,3500,0.035,18000,400,340,0.06,
      100,0.2,0.85,0.4,0.6,0.85,0.15,0.003, 350,0.7,1.3,350,3.5,0.0,350,400,0},
     0.005f, 0.5f, 0.99f},

    /* 20: Tryptophan-like (protein) */
    {"Tryptophan-like", "DOM", 280, 340,
     {0,4000,0, 0,200,0, 0,0,0, 340,280,4500,0.04,22000,340,280,0.07,
      150,0.3,1.1,0.7,0.9,1.1,0.4,0.002, 450,1.0,2.0,450,4.5,0.0,450,340,0},
     0.003f, 0.2f, 0.995f},

    /* 21: Tyrosine-like (protein) */
    {"Tyrosine-like", "DOM", 275, 310,
     {2000,0,0, 0,100,0, 0,0,0, 310,275,2200,0.02,11000,310,275,0.04,
      70,0.15,0.8,0.4,0.6,0.85,0.1,0.004, 220,0.5,1.0,220,2.2,0.0,220,310,0},
     0.004f, 0.3f, 0.99f},

    /* 22: Crude oil (freshwater) */
    {"Crude oil", "Petroleum", 254, 340,
     {0,3000,0, 0,2000,0, 0,0,0, 340,254,5000,0.05,25000,340,255,0.08,
      200,0.3,1.0,0.6,0.8,1.0,0.3,0.003, 500,1.2,2.0,500,5.0,0.0,500,340,0},
     0.001f, 0.1f, 0.998f},

    /* 23: Diesel fuel */
    {"Diesel fuel", "Petroleum", 254, 320,
     {0,2500,0, 0,1500,0, 0,0,0, 320,254,4000,0.04,20000,320,255,0.07,
      150,0.2,0.9,0.5,0.7,0.9,0.2,0.003, 400,1.0,1.8,400,4.0,0.0,400,320,0},
     0.002f, 0.2f, 0.996f},

    /* 24: Motor oil */
    {"Motor oil", "Petroleum", 280, 360,
     {0,2000,0, 0,3000,0, 0,500,0, 360,280,5500,0.05,28000,360,280,0.09,
      250,0.3,1.2,0.8,1.0,1.2,0.4,0.002, 550,1.5,2.5,550,5.5,0.0,550,360,0},
     0.001f, 0.15f, 0.997f},

    /* 25: Gasoline */
    {"Gasoline", "Petroleum", 254, 310,
     {0,2500,0, 0,800,0, 0,0,0, 310,254,3300,0.03,16000,310,255,0.05,
      100,0.2,0.85,0.4,0.6,0.85,0.15,0.004, 330,0.7,1.3,330,3.3,0.0,330,310,0},
     0.002f, 0.2f, 0.995f},

    /* 26: BTEX mixture */
    {"BTEX mixture", "Petroleum", 254, 290,
     {0,3000,0, 0,500,0, 0,0,0, 290,254,3500,0.035,17000,290,255,0.06,
      120,0.2,0.9,0.5,0.7,0.9,0.2,0.003, 350,0.8,1.5,350,3.5,0.0,350,290,0},
     0.002f, 0.2f, 0.995f},

    /* 27: PAH (naphthalene) */
    {"Naphthalene", "Petroleum", 280, 340,
     {0,3500,0, 0,2000,0, 0,0,0, 340,280,5500,0.05,28000,340,280,0.09,
      200,0.3,1.1,0.7,0.9,1.1,0.4,0.002, 550,1.3,2.3,550,5.5,0.0,550,340,0},
     0.001f, 0.1f, 0.998f},

    /* 28: PAH (phenanthrene) */
    {"Phenanthrene", "Petroleum", 260, 370,
     {2500,0,0, 0,2500,0, 0,0,0, 370,260,5000,0.05,25000,370,255,0.08,
      180,0.3,1.0,0.6,0.8,1.0,0.3,0.003, 500,1.2,2.0,500,5.0,0.0,500,370,0},
     0.001f, 0.1f, 0.998f},

    /* 29: PAH (pyrene) */
    {"Pyrene", "Petroleum", 340, 390,
     {0,0,0, 0,4000,0, 0,0,0, 390,340,4500,0.04,22000,390,340,0.07,
      150,0.2,1.0,0.5,0.7,1.0,0.2,0.003, 450,1.0,1.8,450,4.5,0.0,450,390,0},
     0.001f, 0.1f, 0.998f},

    /* 30: Carbaryl (pesticide) */
    {"Carbaryl", "Pesticide", 280, 340,
     {0,3000,0, 0,1500,0, 0,0,0, 340,280,4500,0.04,22000,340,280,0.07,
      150,0.2,1.0,0.5,0.7,0.9,0.3,0.003, 450,1.0,1.8,450,4.5,0.0,450,340,0},
     0.002f, 0.2f, 0.995f},

    /* 31: Carbofuran */
    {"Carbofuran", "Pesticide", 280, 330,
     {0,2500,0, 0,1000,0, 0,0,0, 330,280,3500,0.03,17000,330,280,0.05,
      100,0.2,0.9,0.4,0.6,0.85,0.2,0.003, 350,0.8,1.5,350,3.5,0.0,350,330,0},
     0.003f, 0.3f, 0.99f},

    /* 32: Chlorpyrifos */
    {"Chlorpyrifos", "Pesticide", 290, 350,
     {0,2000,0, 0,2000,0, 0,0,0, 350,290,4000,0.04,20000,350,280,0.06,
      130,0.2,0.95,0.5,0.7,0.9,0.25,0.003, 400,0.9,1.6,400,4.0,0.0,400,350,0},
     0.003f, 0.3f, 0.99f},

    /* 33: Atrazine */
    {"Atrazine", "Pesticide", 254, 310,
     {0,2000,0, 0,500,0, 0,0,0, 310,254,2500,0.025,12000,310,255,0.04,
      80,0.15,0.8,0.3,0.5,0.8,0.1,0.004, 250,0.6,1.2,250,2.5,0.0,250,310,0},
     0.004f, 0.4f, 0.985f},

    /* 34: Aspirin */
    {"Aspirin", "Pharmaceutical", 280, 350,
     {0,2500,0, 0,1500,0, 0,0,0, 350,280,4000,0.04,20000,350,280,0.06,
      130,0.2,0.95,0.5,0.7,0.9,0.25,0.003, 400,0.9,1.6,400,4.0,0.0,400,350,0},
     0.003f, 0.3f, 0.99f},

    /* 35: Paracetamol */
    {"Paracetamol", "Pharmaceutical", 280, 360,
     {0,2000,0, 0,2000,0, 0,0,0, 360,280,4000,0.04,20000,360,280,0.07,
      140,0.2,1.0,0.5,0.7,0.9,0.3,0.003, 400,1.0,1.7,400,4.0,0.0,400,360,0},
     0.003f, 0.3f, 0.99f},

    /* 36: Caffeine */
    {"Caffeine", "Pharmaceutical", 275, 340,
     {0,1500,0, 0,1000,0, 0,0,0, 340,275,2500,0.025,12000,340,280,0.04,
      80,0.15,0.8,0.3,0.5,0.8,0.1,0.004, 250,0.6,1.2,250,2.5,0.0,250,340,0},
     0.004f, 0.4f, 0.985f},

    /* 37: Warfarin */
    {"Warfarin", "Pharmaceutical", 320, 400,
     {0,0,0, 0,3000,0, 0,0,0, 400,320,3500,0.035,18000,400,340,0.06,
      120,0.2,0.9,0.5,0.7,0.9,0.2,0.003, 350,0.8,1.5,350,3.5,0.0,350,400,0},
     0.003f, 0.3f, 0.99f},

    /* 38: Doxorubicin */
    {"Doxorubicin", "Pharmaceutical", 470, 590,
     {0,0,0, 0,0,0, 0,0,7000, 590,470,8000,0.08,40000,590,470,0.13,
      280,0.5,1.4,0.9,1.1,1.3,0.5,0.002, 800,2.0,3.0,800,8.0,0.0,800,590,0},
     0.001f, 0.05f, 0.999f},

    /* 39: Hoechst 33342 */
    {"Hoechst 33342", "DNA stain", 360, 460,
     {0,0,0, 0,6000,0, 0,0,0, 460,365,7000,0.07,35000,460,365,0.11,
      200,0.4,1.3,0.8,1.0,1.2,0.5,0.002, 700,1.5,2.5,700,7.0,0.0,700,460,0},
     0.002f, 0.1f, 0.997f},

    /* 40: SYBR Green */
    {"SYBR Green", "DNA stain", 470, 520,
     {0,0,0, 0,0,0, 0,0,8000, 520,470,10000,0.10,50000,520,470,0.17,
      500,0.7,1.7,1.2,1.4,1.5,0.8,0.001, 1000,2.5,3.5,1000,10.0,0.0,1000,520,0},
     0.0005f, 0.02f, 0.9999f},

    /* 41: Ethidium bromide */
    {"Ethidium bromide", "DNA stain", 300, 600,
     {0,3000,0, 0,2000,0, 0,0,5000, 600,300,5000,0.05,25000,600,280,0.08,
      150,0.3,1.0,0.5,0.7,1.0,0.2,0.003, 500,1.2,2.0,500,5.0,0.0,500,600,0},
     0.002f, 0.1f, 0.997f},

    /* 42: PicoGreen */
    {"PicoGreen", "DNA quant assay", 470, 520,
     {0,0,0, 0,0,0, 0,0,9000, 520,470,11000,0.11,55000,520,470,0.18,
      550,0.75,1.65,1.3,1.4,1.5,0.9,0.001, 1100,2.8,3.8,1100,11.0,0.0,1100,520,0},
     0.0003f, 0.01f, 0.9999f},

    /* 43: Coenzyme Q10 */
    {"Coenzyme Q10", "Supplement", 280, 350,
     {0,2000,0, 0,1500,0, 0,0,0, 350,280,3500,0.035,18000,350,280,0.06,
      120,0.2,0.95,0.5,0.7,0.9,0.25,0.003, 350,0.8,1.5,350,3.5,0.0,350,350,0},
     0.003f, 0.3f, 0.99f},

    /* 44: Curcumin */
    {"Curcumin", "Natural compound", 440, 540,
     {0,0,0, 0,0,0, 0,0,6000, 540,440,7000,0.07,35000,540,440,0.12,
      250,0.4,1.3,0.8,1.0,1.2,0.5,0.002, 700,1.8,2.8,700,7.0,0.0,700,540,0},
     0.002f, 0.1f, 0.997f},

    /* 45: Olive oil (extra virgin) */
    {"Olive oil EVOO", "Food", 360, 440,
     {0,0,0, 0,5000,0, 0,1000,0, 440,365,6000,0.06,30000,440,365,0.10,
      200,0.4,1.3,0.8,1.0,1.2,0.5,0.002, 600,1.5,2.5,600,6.0,0.0,600,440,0},
     0.001f, 0.1f, 0.998f},

    /* 46: Honey (pure clover) */
    {"Honey (clover)", "Food", 360, 420,
     {0,0,0, 0,4000,0, 0,500,0, 420,365,4500,0.045,22000,420,365,0.07,
      150,0.3,1.1,0.6,0.8,1.0,0.4,0.002, 450,1.0,2.0,450,4.5,0.0,450,420,0},
     0.002f, 0.15f, 0.996f},

    /* 47: Beer (fresh lager) */
    {"Beer (lager)", "Beverage", 340, 440,
     {0,0,0, 0,3500,0, 0,300,0, 440,340,3800,0.04,19000,440,340,0.06,
      120,0.2,1.0,0.5,0.7,0.9,0.3,0.003, 380,0.9,1.7,380,3.8,0.0,380,440,0},
     0.003f, 0.2f, 0.995f},

    /* 48: Wine (red, resveratrol) */
    {"Wine (red)", "Beverage", 340, 390,
     {0,0,0, 0,3000,0, 0,200,0, 390,340,3200,0.03,16000,390,340,0.05,
      100,0.2,0.9,0.4,0.6,0.85,0.2,0.003, 320,0.8,1.5,320,3.2,0.0,320,390,0},
     0.004f, 0.3f, 0.99f},

    /* 49: Tap water (baseline) */
    {"Tap water", "Reference", 254, 350,
     {0,200,0, 0,100,0, 0,0,0, 350,254,300,0.003,1500,350,255,0.01,
      10,0.05,0.5,0.1,0.2,0.5,0.02,0.005, 30,0.1,0.3,30,0.3,0.0,30,350,0},
     0.01f, 1.0f, 0.9f},
};

/* ── Private: Feature variance for inverse-variance weighting ── */
static float feature_variance[FEATURE_COUNT];

/* ── Public Functions ─────────────────────────────────── */

void library_init(void)
{
    /* Compute approximate feature variance from library for distance weighting */
    for (int f = 0; f < FEATURE_COUNT; f++) {
        float mean = 0;
        for (int i = 0; i < LIBRARY_SIZE; i++) {
            mean += default_library[i].features[f];
        }
        mean /= LIBRARY_SIZE;

        float var = 0;
        for (int i = 0; i < LIBRARY_SIZE; i++) {
            float d = default_library[i].features[f] - mean;
            var += d * d;
        }
        var /= LIBRARY_SIZE;
        feature_variance[f] = (var > 1e-10f) ? var : 1.0f;
    }
}

uint8_t library_size(void)
{
    return LIBRARY_SIZE;
}

const library_entry_t *library_get(uint8_t index)
{
    if (index >= LIBRARY_SIZE) return NULL;
    return &default_library[index];
}

int library_find(const char *name)
{
    if (!name) return -1;
    for (int i = 0; i < LIBRARY_SIZE; i++) {
        /* Case-insensitive comparison */
        if (strncasecmp(default_library[i].name, name, 31) == 0) {
            return i;
        }
    }
    return -1;
}

int library_classify(const eem_t *eem, classify_result_t *result)
{
    if (!eem || !result) return -1;

    /* Compute weighted Euclidean distance to each library entry */
    float distances[LIBRARY_SIZE];

    for (int i = 0; i < LIBRARY_SIZE; i++) {
        float dist = 0;
        for (int f = 0; f < FEATURE_COUNT; f++) {
            float d = eem->features[f] - default_library[i].features[f];
            float w = 1.0f / sqrtf(feature_variance[f] + 1e-6f);
            dist += d * d * w * w;
        }
        distances[i] = sqrtf(dist);
    }

    /* Find k=5 nearest neighbors (simple selection sort on small array) */
    uint8_t indices[LIBRARY_SIZE];
    for (int i = 0; i < LIBRARY_SIZE; i++) indices[i] = i;

    /* Partial selection sort for first K elements */
    for (int k = 0; k < KNN_K; k++) {
        int min_idx = k;
        for (int j = k + 1; j < LIBRARY_SIZE; j++) {
            if (distances[indices[j]] < distances[indices[min_idx]]) {
                min_idx = j;
            }
        }
        /* Swap */
        uint8_t tmp = indices[k];
        indices[k] = indices[min_idx];
        indices[min_idx] = tmp;
    }

    /* Fill result */
    memset(result, 0, sizeof(classify_result_t));
    for (int k = 0; k < KNN_K; k++) {
        result->indices[k] = indices[k];
        result->distances[k] = distances[indices[k]];
    }

    /* Convert distances to confidences using softmax */
    float max_dist = result->distances[0];
    float sum_exp = 0;
    float temp = 0.1f * max_dist + 1e-6f;  /* temperature scaling */

    float exps[KNN_K];
    for (int k = 0; k < KNN_K; k++) {
        exps[k] = expf(-(result->distances[k] - max_dist) / temp);
        sum_exp += exps[k];
    }
    for (int k = 0; k < KNN_K; k++) {
        result->confidences[k] = (sum_exp > 0) ? exps[k] / sum_exp : 0;
    }

    result->top_match = result->indices[0];
    result->top_confidence = result->confidences[0];

    /* Estimate concentration if confidence is high enough */
    if (result->top_confidence > 0.5f) {
        const library_entry_t *entry = &default_library[result->top_match];
        float intensity = eem->features[26];  /* peak intensity feature */
        result->estimated_conc = library_estimate_concentration(entry, intensity);
    } else {
        result->estimated_conc = -1;
    }

    return 0;
}

float library_estimate_concentration(const library_entry_t *entry, float intensity)
{
    if (!entry || intensity <= 0) return -1;
    /* Linear calibration: conc = a × intensity + b */
    float conc = entry->calib_a * intensity + entry->calib_b;
    if (conc < 0) conc = 0;
    return conc;
}

float library_stern_volmer_correct(float F0, float Ksv, float Q)
{
    /* F0/F = 1 + Ksv × Q  →  F0 = F × (1 + Ksv × Q)
     * Here we compute the unquenched fluorescence from observed */
    return F0 * (1.0f + Ksv * Q);
}

int library_update(uint8_t index, const library_entry_t *entry)
{
    if (index >= LIBRARY_SIZE || !entry) return -1;
    memcpy(&default_library[index], entry, sizeof(library_entry_t));
    return 0;
}

int library_save(void)
{
    /* In production: write to W25Q128 SPI flash
     * For now: library is in RAM, lost on power-off
     * A real implementation would use HAL_FLASHEx_DATAEEPROM or external flash */
    return 0;
}