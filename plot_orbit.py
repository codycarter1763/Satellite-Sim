#!/usr/bin/env python3
"""
plot_orbit.py

Reads the Trick/JEOD orbit log (log_vehicle_state.csv) and verifies
the vehicle is actually orbiting under Earth's gravity, not drifting
in a straight line.

Usage:
    python3 plot_orbit.py SET_test/RUN_test/log_vehicle_state.csv
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MU_EARTH = 3.986004418e14   # Earth gravitational parameter, m^3/s^2
EARTH_RADIUS = 6378000.0    # m


def find_col(columns, must_contain):
    """Match a column name loosely -- Trick's headers include units
    in {braces} and full dotted variable paths, so match by substring
    rather than requiring an exact string."""
    for c in columns:
        if all(tok in c for tok in must_contain):
            return c
    raise KeyError(f"Could not find a column containing {must_contain}\n"
                    f"Available columns:\n  " + "\n  ".join(columns))


def main():
    if len(sys.argv) < 2:
        print("Usage: plot_orbit.py <log_vehicle_state.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]

    df = pd.read_csv(csv_path, skipinitialspace=True)
    columns = list(df.columns)

    time_col = find_col(columns, ["sys.exec.out.time"])
    x_col    = find_col(columns, ["position[0]"])
    y_col    = find_col(columns, ["position[1]"])
    z_col    = find_col(columns, ["position[2]"])

    t = df[time_col].to_numpy()
    x = df[x_col].to_numpy()
    y = df[y_col].to_numpy()
    z = df[z_col].to_numpy()

    r = np.sqrt(x**2 + y**2 + z**2)

    print(f"Loaded {len(t)} samples spanning t = {t[0]:.1f}s to {t[-1]:.1f}s")
    print(f"Orbital radius: min = {r.min():.1f} m, max = {r.max():.1f} m, "
          f"mean = {r.mean():.1f} m")
    print(f"Radius variation: {100 * (r.max() - r.min()) / r.mean():.4f}% "
          f"(near-zero = circular orbit)")

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # ---- Plot 1: Orbit trace (X-Y plane), Earth to scale ----
    ax = axes[0]
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.fill(EARTH_RADIUS * np.cos(theta), EARTH_RADIUS * np.sin(theta),
            color="#99c2ff", label="Earth")
    ax.plot(x, y, "b-", linewidth=1.5, label="Trajectory")
    ax.plot(x[0], y[0], "go", markersize=8, label="Start")
    ax.plot(x[-1], y[-1], "ro", markersize=8, label="End")
    ax.plot(0, 0, "k+", markersize=12, mew=2, label="Earth center")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Position X (m)")
    ax.set_ylabel("Position Y (m)")
    ax.set_title("Vehicle Orbit Around Earth (X-Y plane)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True)

    # ---- Plot 2: Orbital radius vs time ----
    ax = axes[1]
    ax.plot(t, r / 1000.0, "b-", linewidth=1.5)
    ax.axhline(r.mean() / 1000.0, color="r", linestyle="--",
               label="mean radius")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Distance from Earth center (km)")
    ax.set_title("Orbital Radius vs Time\n(near-constant = circular orbit)")
    ax.legend()
    ax.grid(True)

    # ---- Plot 3: Early trajectory vs analytical projectile curve ----
    ax = axes[2]
    n_check = min(10, len(t))
    t_check = t[:n_check]
    x_check = x[:n_check]

    a_grav = MU_EARTH / x[0]**2
    x_theory = x[0] - 0.5 * a_grav * t_check**2

    ax.plot(t_check, x_check, "bo-", linewidth=1.5,
            markerfacecolor="b", label="JEOD simulated")
    ax.plot(t_check, x_theory, "r--", linewidth=1.5,
            label=r"Analytical: $x_0 - \frac{1}{2}at^2$")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Position X (m)")
    ax.set_title("Early Trajectory Validation\n(confirms gravity is applied)")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    out_path = "orbit_verification.png"
    plt.savefig(out_path, dpi=150)
    print(f"\nSaved plot to {out_path}")

    print("\nIf plot 1 shows a closed loop around Earth, plot 2 stays "
          "roughly flat,\nand plot 3's two curves overlap, gravity is "
          "being applied correctly.")

    plt.show()


if __name__ == "__main__":
    main()