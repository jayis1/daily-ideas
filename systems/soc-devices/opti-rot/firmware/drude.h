/*
 * drude.h — Drude optical rotatory dispersion (ORD) analysis
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Fits the Drude equation [α](λ) = K / (λ² - λ₀²) to multi-wavelength
 * rotation measurements to estimate K (strength) and λ₀ (absorption
 * wavelength near an electronic transition).
 */
#ifndef DRUDE_H
#define DRUDE_H

typedef struct {
    double K;           /* Drude strength constant */
    double lambda0_nm;  /* Characteristic absorption wavelength (nm) */
    double residual;    /* Fit residual (sum of squared errors) */
    bool   valid;       /* true if fit converged */
} drude_result_t;

/*
 * Fit Drude equation to rotation measurements at N wavelengths.
 * alphas[]  = specific rotations (degrees, temp-corrected to 20°C)
 * lambdas[] = wavelengths in nm
 * n         = number of points (typically 3)
 */
drude_result_t drude_fit(const double *alphas, const double *lambdas, int n);

/* Predict specific rotation at an arbitrary wavelength given Drude params */
double drude_predict(double K, double lambda0, double wavelength_nm);

#endif /* DRUDE_H */