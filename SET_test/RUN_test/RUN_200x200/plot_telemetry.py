import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("=" * 60)
print("NASA Trick / JEOD Telemetry Analysis")
print("=" * 60)

FILE = "log_state.csv"

df = pd.read_csv(FILE)

print(f"File:       {FILE}")
print(f"Samples:    {len(df)}")

# ------------------------------------------------------------
# Rename Trick DRAscii columns
# ------------------------------------------------------------

df.rename(columns={
    "sys.exec.out.time {s}":
        "time",

    "vehicle.dyn_body.composite_body.state.trans.position[0] {m}":
        "px",
    "vehicle.dyn_body.composite_body.state.trans.position[1] {m}":
        "py",
    "vehicle.dyn_body.composite_body.state.trans.position[2] {m}":
        "pz",

    "vehicle.dyn_body.composite_body.state.trans.velocity[0] {m/s}":
        "vx",
    "vehicle.dyn_body.composite_body.state.trans.velocity[1] {m/s}":
        "vy",
    "vehicle.dyn_body.composite_body.state.trans.velocity[2] {m/s}":
        "vz",

    "interactions.aero_drag.aero_force[0] {N}":
        "drag_x",
    "interactions.aero_drag.aero_force[1] {N}":
        "drag_y",
    "interactions.aero_drag.aero_force[2] {N}":
        "drag_z",

    "vehicle.atmos_state.density {kg/m3}":
        "density",
    "vehicle.atmos_state.pressure {N/m2}":
        "pressure",
    "vehicle.atmos_state.temperature {K}":
        "temperature",

    "vehicle.lvlh_frame.frame.state.rot.Q_parent_this.scalar {--}":
        "qw",
    "vehicle.lvlh_frame.frame.state.rot.Q_parent_this.vector[0] {--}":
        "qx",
    "vehicle.lvlh_frame.frame.state.rot.Q_parent_this.vector[1] {--}":
        "qy",
    "vehicle.lvlh_frame.frame.state.rot.Q_parent_this.vector[2] {--}":
        "qz",
}, inplace=True)

# ------------------------------------------------------------
# Verify required columns
# ------------------------------------------------------------

required_columns = [
    "time",
    "px", "py", "pz",
    "vx", "vy", "vz",
    "qw", "qx", "qy", "qz",
    "drag_x", "drag_y", "drag_z",
    "density",
    "pressure",
    "temperature",
]

missing = [col for col in required_columns if col not in df.columns]

if missing:
    print()
    print("ERROR: Missing required columns:")
    for col in missing:
        print(f"  {col}")

    print()
    print("Available columns:")
    for col in df.columns:
        print(f"  {col}")

    raise RuntimeError("Required telemetry columns are missing.")

# ------------------------------------------------------------
# Convert numeric columns
# ------------------------------------------------------------

for col in required_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ------------------------------------------------------------
# Derived telemetry
# ------------------------------------------------------------

df["radius"] = np.sqrt(
    df["px"]**2 +
    df["py"]**2 +
    df["pz"]**2
)

df["velocity"] = np.sqrt(
    df["vx"]**2 +
    df["vy"]**2 +
    df["vz"]**2
)

df["drag"] = np.sqrt(
    df["drag_x"]**2 +
    df["drag_y"]**2 +
    df["drag_z"]**2
)

# ------------------------------------------------------------
# Earth constants
# ------------------------------------------------------------

EARTH_RADIUS = 6_371_000.0
EARTH_ROTATION_RATE = 7.2921151467e-5
INITIAL_EARTH_ROTATION = 0.0

# ------------------------------------------------------------
# Calculate altitude
# ------------------------------------------------------------

df["altitude"] = df["radius"] - EARTH_RADIUS

# ------------------------------------------------------------
# ECI -> ECEF
# ------------------------------------------------------------

theta = (
    INITIAL_EARTH_ROTATION +
    EARTH_ROTATION_RATE * df["time"]
)

cos_theta = np.cos(theta)
sin_theta = np.sin(theta)

df["ecef_x"] = (
    cos_theta * df["px"] +
    sin_theta * df["py"]
)

df["ecef_y"] = (
    -sin_theta * df["px"] +
    cos_theta * df["py"]
)

df["ecef_z"] = df["pz"]

# ------------------------------------------------------------
# Calculate latitude / longitude
# ------------------------------------------------------------

df["latitude"] = np.degrees(
    np.arctan2(
        df["ecef_z"],
        np.sqrt(
            df["ecef_x"]**2 +
            df["ecef_y"]**2
        )
    )
)

df["longitude"] = np.degrees(
    np.arctan2(
        df["ecef_y"],
        df["ecef_x"]
    )
)

# ------------------------------------------------------------
# Remove invalid startup samples
# ------------------------------------------------------------

valid = (
    (df["radius"] > 6_000_000) &
    df["time"].notna()
)

df_valid = df[valid].copy()

print(f"Valid samples: {len(df_valid)}")

# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

print()
print("ORBIT")
print("-" * 60)

print(
    f"Altitude min:      "
    f"{df_valid['altitude'].min() / 1000:.2f} km"
)

print(
    f"Altitude max:      "
    f"{df_valid['altitude'].max() / 1000:.2f} km"
)

print(
    f"Altitude mean:     "
    f"{df_valid['altitude'].mean() / 1000:.2f} km"
)

print()

print(
    f"Velocity min:      "
    f"{df_valid['velocity'].min() / 1000:.4f} km/s"
)

print(
    f"Velocity max:      "
    f"{df_valid['velocity'].max() / 1000:.4f} km/s"
)

print(
    f"Velocity mean:     "
    f"{df_valid['velocity'].mean() / 1000:.4f} km/s"
)

print()
print("ATMOSPHERE")
print("-" * 60)

print(
    f"Density min:       "
    f"{df_valid['density'].min():.4e} kg/m^3"
)

print(
    f"Density max:       "
    f"{df_valid['density'].max():.4e} kg/m^3"
)

print(
    f"Temperature min:   "
    f"{df_valid['temperature'].min():.2f} K"
)

print(
    f"Temperature max:   "
    f"{df_valid['temperature'].max():.2f} K"
)

print()
print("AERODYNAMICS")
print("-" * 60)

print(
    f"Drag min:          "
    f"{df_valid['drag'].min():.4e} N"
)

print(
    f"Drag max:          "
    f"{df_valid['drag'].max():.4e} N"
)

print(
    f"Drag mean:         "
    f"{df_valid['drag'].mean():.4e} N"
)

# ------------------------------------------------------------
# NumPy arrays
# ------------------------------------------------------------

t = df_valid["time"].to_numpy()

altitude = df_valid["altitude"].to_numpy() / 1000
velocity = df_valid["velocity"].to_numpy() / 1000
radius = df_valid["radius"].to_numpy() / 1000

latitude = df_valid["latitude"].to_numpy()
longitude = df_valid["longitude"].to_numpy()

density = df_valid["density"].to_numpy()
temperature = df_valid["temperature"].to_numpy()
drag = df_valid["drag"].to_numpy()

px = df_valid["px"].to_numpy() / 1000
py = df_valid["py"].to_numpy() / 1000
pz = df_valid["pz"].to_numpy() / 1000

vx = df_valid["vx"].to_numpy() / 1000
vy = df_valid["vy"].to_numpy() / 1000
vz = df_valid["vz"].to_numpy() / 1000

# ------------------------------------------------------------
# 1. Altitude
# ------------------------------------------------------------

plt.figure()
plt.plot(t, altitude)
plt.xlabel("Time (s)")
plt.ylabel("Altitude (km)")
plt.title("Spacecraft Altitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 2. Velocity
# ------------------------------------------------------------

plt.figure()
plt.plot(t, velocity)
plt.xlabel("Time (s)")
plt.ylabel("Velocity (km/s)")
plt.title("Orbital Velocity")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 3. Orbital radius
# ------------------------------------------------------------

plt.figure()
plt.plot(t, radius)
plt.xlabel("Time (s)")
plt.ylabel("Radius from Earth Center (km)")
plt.title("Orbital Radius")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 4. Latitude
# ------------------------------------------------------------

plt.figure()
plt.plot(t, latitude)
plt.xlabel("Time (s)")
plt.ylabel("Latitude (deg)")
plt.title("Spacecraft Latitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 5. Longitude
# ------------------------------------------------------------

plt.figure()
plt.plot(t, longitude)
plt.xlabel("Time (s)")
plt.ylabel("Longitude (deg)")
plt.title("Spacecraft Longitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 6. Ground track
# ------------------------------------------------------------

plt.figure()

plt.plot(
    longitude,
    latitude
)

plt.xlabel("Longitude (deg)")
plt.ylabel("Latitude (deg)")
plt.title("Orbital Ground Track")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 7. Atmospheric density vs altitude
# ------------------------------------------------------------

positive_density = density > 0

plt.figure()
plt.semilogy(
    altitude[positive_density],
    density[positive_density],
    "."
)
plt.xlabel("Altitude (km)")
plt.ylabel("Atmospheric Density (kg/m³)")
plt.title("Atmospheric Density vs Altitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 8. Atmospheric temperature
# ------------------------------------------------------------

plt.figure()
plt.plot(altitude, temperature, ".")
plt.xlabel("Altitude (km)")
plt.ylabel("Temperature (K)")
plt.title("Atmospheric Temperature vs Altitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 9. Drag force
# ------------------------------------------------------------

positive_drag = drag > 0

plt.figure()
plt.semilogy(
    t[positive_drag],
    drag[positive_drag]
)
plt.xlabel("Time (s)")
plt.ylabel("Drag Force (N)")
plt.title("Aerodynamic Drag")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 10. Drag vs atmospheric density
# ------------------------------------------------------------

valid_drag_density = (
    (density > 0) &
    (drag > 0)
)

plt.figure()
plt.loglog(
    density[valid_drag_density],
    drag[valid_drag_density],
    "."
)
plt.xlabel("Atmospheric Density (kg/m³)")
plt.ylabel("Drag Force (N)")
plt.title("Drag Force vs Atmospheric Density")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 11. Velocity vs altitude
# ------------------------------------------------------------

plt.figure()
plt.plot(altitude, velocity, ".")
plt.xlabel("Altitude (km)")
plt.ylabel("Velocity (km/s)")
plt.title("Orbital Velocity vs Altitude")
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 12. ECI position
# ------------------------------------------------------------

plt.figure()
plt.plot(t, px, label="X")
plt.plot(t, py, label="Y")
plt.plot(t, pz, label="Z")
plt.xlabel("Time (s)")
plt.ylabel("Position (km)")
plt.title("ECI Position Components")
plt.legend()
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 13. ECI velocity
# ------------------------------------------------------------

plt.figure()
plt.plot(t, vx, label="Vx")
plt.plot(t, vy, label="Vy")
plt.plot(t, vz, label="Vz")
plt.xlabel("Time (s)")
plt.ylabel("Velocity (km/s)")
plt.title("ECI Velocity Components")
plt.legend()
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 14. ECEF position
# ------------------------------------------------------------

ecef_x = df_valid["ecef_x"].to_numpy() / 1000
ecef_y = df_valid["ecef_y"].to_numpy() / 1000
ecef_z = df_valid["ecef_z"].to_numpy() / 1000

plt.figure()
plt.plot(t, ecef_x, label="X")
plt.plot(t, ecef_y, label="Y")
plt.plot(t, ecef_z, label="Z")
plt.xlabel("Time (s)")
plt.ylabel("Position (km)")
plt.title("ECEF Position Components")
plt.legend()
plt.grid(True)
plt.tight_layout()

# ------------------------------------------------------------
# 15. Orbit path centered on Earth
# ------------------------------------------------------------

plt.figure(figsize=(8, 8))

# ECI position relative to Earth's center
plt.plot(
    px,
    py,
    label="Spacecraft Orbit"
)

# Earth
earth = plt.Circle(
    (0, 0),
    EARTH_RADIUS / 1000,
    fill=False,
    linewidth=2,
    label="Earth"
)

plt.gca().add_patch(earth)

# Earth center
plt.plot(
    0,
    0,
    "o",
    markersize=5,
    label="Earth Center"
)

# Spacecraft starting position
plt.plot(
    px[0],
    py[0],
    "o",
    markersize=6,
    label="Initial Position"
)

# Current/final position
plt.plot(
    px[-1],
    py[-1],
    "o",
    markersize=6,
    label="Final Position"
)

plt.xlabel("ECI X Position (km)")
plt.ylabel("ECI Y Position (km)")
plt.title("Spacecraft Orbital Path")
plt.axis("equal")
plt.grid(True)
plt.legend()
plt.tight_layout()

# ------------------------------------------------------------
# Show all plots
# ------------------------------------------------------------

plt.show()