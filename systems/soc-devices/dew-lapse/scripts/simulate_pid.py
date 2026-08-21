#!/usr/bin/env python3
"""simulate_pid.py — simulate the Frost Point mirror-tracking PID loop.

Useful for tuning PID gains before flashing. Models the mirror as a
first-order thermal mass with a TEC cooling power proportional to
current, plus a latent-heat term when condensation is present.
"""
import argparse
import math


def sat_vp(t_c: float, over_water: bool = True) -> float:
    """Saturation vapor pressure (hPa), Magnus-Tetens Sonntag94."""
    if over_water:
        return 6.116441 * math.exp(17.625 * t_c / (243.04 + t_c))
    return 6.109217 * math.exp(21.875 * t_c / (265.5 + t_c))


class Mirror:
    """First-order thermal model of the mirror + film."""

    def __init__(self, t_air=25.0, rh=50.0, thermal_mass=0.5):
        self.t_air = t_air
        self.rh = rh
        self.t_mirror = t_air
        self.t_ref = t_air
        self.thermal_mass = thermal_mass  # J/K
        self.film_present = False

    def step(self, tec_frac: float, dt: float) -> tuple:
        """Apply TEC drive for dt seconds, return (t_mirror, t_ref, dt_mirror)."""
        # TEC cooling power: simplified linear model
        # Q_cold = alpha * I * T - 0.5 * I^2 * R  (peltier equation)
        # We approximate: Q = 3.0 * tec_frac * (self.t_mirror - 5)  (watts)
        tec_q = 3.0 * tec_frac * (self.t_mirror - 5.0)
        # Heat leak from ambient
        q_leak = (self.t_air - self.t_mirror) / 5.0  # K/W
        # Latent heat: if film present and t_mirror below dew point, film grows
        dew = self._dew_point()
        if self.t_mirror < dew:
            self.film_present = True
            # Latent heat flux ~ proportional to (dew - t_mirror)
            q_latent = 0.02 * (dew - self.t_mirror)  # W
        else:
            # Film evaporates
            if self.film_present:
                q_latent = -0.05 * (self.t_mirror - dew)
            else:
                q_latent = 0.0
            if self.t_mirror > dew + 0.5:
                self.film_present = False

        dT = (tec_q + q_leak + q_latent) * dt / self.thermal_mass
        self.t_mirror += dT
        # Reference thermistor tracks ambient closely
        self.t_ref += (self.t_air - self.t_ref) * dt / 2.0

        # When film present, mirror is slightly cooler than reference
        if self.film_present:
            dt_m = -0.08  # K, the film setpoint
        else:
            dt_m = 0.0
        return self.t_mirror, self.t_ref, dt_m

    def _dew_point(self) -> float:
        e = sat_vp(self.t_air) * self.rh / 100.0
        a, b = 17.625, 243.04
        alpha = math.log(e / 6.116441)
        return (b * alpha) / (a - alpha)


def simulate(kp=120, ki=4, kd=1800, duration=120, dt=0.1, setpoint=-0.10):
    mirror = Mirror()
    integ = 0.0
    prev_err = 0.0
    t_history, m_history, d_history = [], [], []
    t = 0.0
    while t < duration:
        tm, tr, dtm = mirror.step(0, 0)  # read current state (no drive)
        err = setpoint - dtm
        integ += err * dt
        deriv = (err - prev_err) / dt
        prev_err = err
        out = kp * err + ki * integ + kd * deriv
        out = max(-0.9, min(0.9, out))
        tm, tr, dtm = mirror.step(out, dt)
        t_history.append(t)
        m_history.append(tm)
        d_history.append(dtm)
        t += dt
    return t_history, m_history, d_history


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kp", type=float, default=120)
    p.add_argument("--ki", type=float, default=4)
    p.add_argument("--kd", type=float, default=1800)
    p.add_argument("--duration", type=float, default=120)
    p.add_argument("--dt", type=float, default=0.1)
    args = p.parse_args()

    t, m, d = simulate(args.kp, args.ki, args.kd, args.duration, args.dt)
    print(f"Simulated {args.duration}s with Kp={args.kp} Ki={args.ki} Kd={args.kd}")
    print(f"Final mirror temp: {m[-1]:.3f} °C  (dew point target ~9.3 °C)")
    print(f"Settling time: estimate from plot")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        ax1.plot(t, m, label="Mirror T")
        ax1.axhline(9.3, color="r", linestyle="--", label="Dew point (target)")
        ax1.set_ylabel("Mirror Temp (°C)")
        ax1.legend()
        ax2.plot(t, d, label="ΔT")
        ax2.axhline(-0.10, color="g", linestyle="--", label="Setpoint")
        ax2.set_ylabel("ΔT (K)")
        ax2.set_xlabel("Time (s)")
        ax2.legend()
        fig.tight_layout()
        fig.savefig("pid_sim.png", dpi=120)
        print("Wrote pid_sim.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()