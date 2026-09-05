#!/usr/bin/env python3

import argparse
import csv
import math
import socket
import struct
import time


# ============================================================
# Configuration
# ============================================================

TRICK_HOST = "localhost"

UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005

CYCLE_SEC = 0.10

VEHICLE_NAME = "vehicle"

# Telemetry output
TELEMETRY_FILE = "telemetry.csv"

# Earth rotation rate [rad/s]
EARTH_ROTATION_RATE = 7.2921151467e-5

# Earth mean radius [m]
EARTH_RADIUS = 6_371_000.0

# Initial Greenwich angle
INITIAL_EARTH_ROTATION = 0.0

# Trick variable server broadcast channel
TRICK_BROADCAST_ADDR = "224.3.14.15"
TRICK_BROADCAST_PORT = 9265


# ============================================================
# Trick variables
#
# 17 numeric values total:
#
#   1 simulation time
#   3 position
#   3 velocity
#   4 quaternion
#   3 aerodynamic force
#   3 atmosphere
#
# Trick's Variable Server represents "time" as:
#
#     <time> {s}
#
# Therefore the raw ASCII response contains one additional
# token for the time unit.
# ============================================================

TRICK_VARS = [

    # --------------------------------------------------------
    # Trick simulation time
    # --------------------------------------------------------
    "time",

    # --------------------------------------------------------
    # Position [m]
    # --------------------------------------------------------
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[0]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[1]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[2]",

    # --------------------------------------------------------
    # Velocity [m/s]
    # --------------------------------------------------------
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.velocity[0]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.velocity[1]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.velocity[2]",

    # --------------------------------------------------------
    # Quaternion
    # --------------------------------------------------------
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.scalar",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[0]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[1]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[2]",

    # --------------------------------------------------------
    # Aerodynamic force [N]
    # --------------------------------------------------------
    "interactions.aero_drag.aero_force[0]",
    "interactions.aero_drag.aero_force[1]",
    "interactions.aero_drag.aero_force[2]",

    # --------------------------------------------------------
    # Atmosphere
    #
    # density     [kg/m^3]
    # pressure    [Pa]
    # temperature [K]
    # --------------------------------------------------------
    f"{VEHICLE_NAME}.atmos_state.density",
    f"{VEHICLE_NAME}.atmos_state.pressure",
    f"{VEHICLE_NAME}.atmos_state.temperature",
]


# ============================================================
# ECI -> Latitude / Longitude
# ============================================================

def eci_to_geodetic(x, y, z, sim_time):
    """
    Convert JEOD ECI position [m] to approximate
    geocentric latitude/longitude/altitude.

    Assumes the ECI frame's X axis corresponds to
    Greenwich longitude at simulation time = 0.
    """

    theta = (
        INITIAL_EARTH_ROTATION
        + EARTH_ROTATION_RATE * sim_time
    )

    c = math.cos(theta)
    s = math.sin(theta)

    # --------------------------------------------------------
    # ECI -> ECEF
    # --------------------------------------------------------

    x_ecef = c * x + s * y
    y_ecef = -s * x + c * y
    z_ecef = z

    # --------------------------------------------------------
    # Longitude
    # --------------------------------------------------------

    longitude = math.atan2(
        y_ecef,
        x_ecef
    )

    # --------------------------------------------------------
    # Latitude
    # --------------------------------------------------------

    horizontal = math.sqrt(
        x_ecef * x_ecef +
        y_ecef * y_ecef
    )

    latitude = math.atan2(
        z_ecef,
        horizontal
    )

    # --------------------------------------------------------
    # Radius / altitude
    # --------------------------------------------------------

    radius = math.sqrt(
        x * x +
        y * y +
        z * z
    )

    altitude = radius - EARTH_RADIUS

    # --------------------------------------------------------
    # Convert to degrees
    # --------------------------------------------------------

    latitude_deg = math.degrees(latitude)
    longitude_deg = math.degrees(longitude)

    # --------------------------------------------------------
    # Normalize longitude to [-180, 180]
    # --------------------------------------------------------

    if longitude_deg > 180.0:
        longitude_deg -= 360.0

    if longitude_deg < -180.0:
        longitude_deg += 360.0

    return (
        latitude_deg,
        longitude_deg,
        altitude
    )


# ============================================================
# Variable server discovery
# ============================================================

def parse_broadcast_message(msg: str):

    fields = msg.split("\t")

    if len(fields) < 10:

        raise ValueError(
            f"Unexpected broadcast message format, "
            f"got {len(fields)} fields"
        )

    return {
        "hostname": fields[0],
        "port": int(fields[1]),
        "user": fields[2],
        "pid": int(fields[3]) if fields[3].strip() else None,
        "sim_dir": fields[4],
        "s_main_name": fields[5],
        "input_file": fields[6],
        "trick_version": fields[7],
        "user_tag": fields[8],
    }


def discover_trick_sim(match=None, timeout=30.0):

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    if hasattr(socket, "SO_REUSEPORT"):

        try:

            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEPORT,
                1
            )

        except OSError:

            pass

    sock.bind(
        ("", TRICK_BROADCAST_PORT)
    )

    mreq = struct.pack(
        "4sl",
        socket.inet_aton(
            TRICK_BROADCAST_ADDR
        ),
        socket.INADDR_ANY
    )

    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        mreq
    )

    sock.settimeout(timeout)

    print(
        f"[bridge] Listening for Trick sim broadcasts "
        f"on {TRICK_BROADCAST_ADDR}:{TRICK_BROADCAST_PORT}"
    )

    deadline = time.time() + timeout

    while time.time() < deadline:

        remaining = deadline - time.time()

        sock.settimeout(
            max(remaining, 0.1)
        )

        try:

            raw, _addr = sock.recvfrom(2048)

        except socket.timeout:

            break

        try:

            info = parse_broadcast_message(
                raw.decode(
                    "utf-8",
                    errors="replace"
                )
            )

        except ValueError:

            continue

        print(
            f"[bridge] Found sim: "
            f"{info['sim_dir']} "
            f"(input: {info['input_file']}, "
            f"pid: {info['pid']}, "
            f"host: {info['hostname']}:{info['port']})"
        )

        if match is None:

            sock.close()

            return (
                info["hostname"],
                info["port"]
            )

        haystack = (
            f"{info['sim_dir']} "
            f"{info['input_file']} "
            f"{info['s_main_name']}"
        )

        if match in haystack:

            sock.close()

            return (
                info["hostname"],
                info["port"]
            )

    sock.close()

    raise RuntimeError(
        "No Trick simulation broadcasts seen."
    )


# ============================================================
# Connect to Trick
# ============================================================

def connect_trick(
    host,
    port,
    retries=50,
    delay=0.2
):

    for attempt in range(retries):

        try:

            s = socket.create_connection(
                (host, port),
                timeout=2
            )

            print(
                f"[bridge] Connected to Trick "
                f"variable server on "
                f"{host}:{port}"
            )

            return s

        except (
            ConnectionRefusedError,
            OSError
        ):

            time.sleep(delay)

    raise RuntimeError(
        f"Could not connect to Trick "
        f"variable server on {host}:{port}"
    )


# ============================================================
# Trick communication
# ============================================================

def trick_send(sock, cmd):

    sock.sendall(
        (cmd + "\n").encode("utf-8")
    )


def trick_recv_line(sock, buf):

    while b"\n" not in buf:

        chunk = sock.recv(4096)

        if not chunk:

            raise ConnectionError(
                "Trick variable server "
                "closed connection"
            )

        buf += chunk

    line, _, buf = buf.partition(b"\n")

    return (
        line.decode("utf-8").strip(),
        buf
    )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "port_positional",
        nargs="?",
        type=int,
        default=None
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None
    )

    parser.add_argument(
        "--match",
        type=str,
        default=None
    )

    parser.add_argument(
        "--discovery-timeout",
        type=float,
        default=30.0
    )

    args = parser.parse_args()

    # ========================================================
    # Determine Trick variable server
    # ========================================================

    manual_port = (
        args.port
        if args.port is not None
        else args.port_positional
    )

    if manual_port is not None:

        trick_host = (
            args.host or TRICK_HOST
        )

        trick_port = manual_port

    else:

        trick_host, trick_port = (
            discover_trick_sim(
                match=args.match,
                timeout=args.discovery_timeout
            )
        )

    # ========================================================
    # Open telemetry CSV
    # ========================================================

    telemetry_file = open(
        TELEMETRY_FILE,
        "w",
        newline=""
    )

    telemetry_writer = csv.writer(
        telemetry_file
    )

    telemetry_writer.writerow([
        "time",

        "px",
        "py",
        "pz",

        "vx",
        "vy",
        "vz",

        "qw",
        "qx",
        "qy",
        "qz",

        "drag_x",
        "drag_y",
        "drag_z",

        "density",
        "pressure",
        "temperature",

        "latitude",
        "longitude",
        "altitude"
    ])

    telemetry_file.flush()

    print(
        f"[bridge] Telemetry output: "
        f"{TELEMETRY_FILE}"
    )

    # ========================================================
    # Connect to Trick
    # ========================================================

    trick_sock = connect_trick(
        trick_host,
        trick_port
    )

    # ========================================================
    # Unity UDP socket
    # ========================================================

    unity_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    print(
        f"[bridge] UDP output: "
        f"{UNITY_HOST}:{UNITY_PORT}"
    )

    try:

        # ====================================================
        # Subscribe
        # ====================================================

        print(
            "[bridge] Subscribing to variables..."
        )

        for var in TRICK_VARS:

            print(
                f"[bridge]   {var}"
            )

            trick_send(
                trick_sock,
                f'trick.var_add("{var}")'
            )

        # ====================================================
        # Trick update rate
        # ====================================================

        trick_send(
            trick_sock,
            f"trick.var_cycle({CYCLE_SEC})"
        )

        trick_send(
            trick_sock,
            "trick.var_send()"
        )

        # ====================================================
        # Receive
        # ====================================================

        buf = b""

        first_line_shown = False

        packet_count = 0

        last_print_time = time.time()

        print(
            "[bridge] Waiting for Trick data..."
        )

        while True:

            try:

                line, buf = trick_recv_line(
                    trick_sock,
                    buf
                )

            except ConnectionError as e:

                print(e)

                break

            # ------------------------------------------------
            # First raw message
            # ------------------------------------------------

            if not first_line_shown:

                print()
                print(
                    "=========================================="
                )

                print(
                    "[bridge] First raw Trick message:"
                )

                print(line)

                print(
                    "=========================================="
                )

                print()

                first_line_shown = True

            # ------------------------------------------------
            # Parse Variable Server message
            # ------------------------------------------------

            parts = line.split()

            if not parts:

                continue

            # ------------------------------------------------
            # First field is the VS message type.
            # ------------------------------------------------

            try:

                msg_type = int(parts[0])

            except ValueError:

                continue

            # ------------------------------------------------
            # We only process normal data messages.
            # ------------------------------------------------

            if msg_type != 0:

                continue

            # ------------------------------------------------
            # Trick's "time" variable is formatted as:
            #
            #     <time> {s}
            #
            # Example:
            #
            #     0 41 {s} 7394170.36 ...
            #
            # Therefore:
            #
            #     parts[0] = message type
            #     parts[1] = simulation time
            #     parts[2] = "{s}"
            #     parts[3:] = remaining telemetry
            # ------------------------------------------------

            if len(parts) < 3:

                print(
                    "[bridge] WARNING: malformed "
                    "Variable Server message"
                )

                continue

            # ------------------------------------------------
            # Extract actual Trick simulation time
            # ------------------------------------------------

            try:

                sim_time = float(parts[1])

            except ValueError:

                print(
                    "[bridge] WARNING: invalid "
                    f"simulation time: {parts[1]}"
                )

                continue

            # ------------------------------------------------
            # Remove the time unit token
            # ------------------------------------------------

            if parts[2] == "{s}":

                values = parts[3:]

            else:

                print(
                    "[bridge] WARNING: unexpected "
                    f"time unit '{parts[2]}'"
                )

                values = parts[3:]

            # ------------------------------------------------
            # Remaining numeric telemetry:
            #
            #   3 position
            #   3 velocity
            #   4 quaternion
            #   3 aerodynamic force
            #   3 atmosphere
            #
            # = 16 values
            # ------------------------------------------------

            expected_values = len(TRICK_VARS) - 1

            if len(values) != expected_values:

                print(
                    f"[bridge] WARNING: expected "
                    f"{expected_values} telemetry values "
                    f"after simulation time, "
                    f"got {len(values)}"
                )

                print(
                    "[bridge] Raw message:"
                )

                print(line)

                continue

            # ------------------------------------------------
            # Convert telemetry to floats
            # ------------------------------------------------

            try:

                values = [
                    float(p)
                    for p in values
                ]

            except ValueError as e:

                print(
                    "[bridge] WARNING: could not parse "
                    f"telemetry: {e}"
                )

                print(
                    "[bridge] Raw message:"
                )

                print(line)

                continue

            # ------------------------------------------------
            # Unpack telemetry
            # ------------------------------------------------

            i = 0

            # ------------------------------------------------
            # Position
            # ------------------------------------------------

            px, py, pz = values[i:i + 3]

            i += 3

            # ------------------------------------------------
            # Velocity
            # ------------------------------------------------

            vx, vy, vz = values[i:i + 3]

            i += 3

            # ------------------------------------------------
            # Quaternion
            # ------------------------------------------------

            qw, qx, qy, qz = values[i:i + 4]

            i += 4

            # ------------------------------------------------
            # Aerodynamic force
            # ------------------------------------------------

            drag_x, drag_y, drag_z = values[i:i + 3]

            i += 3

            # ------------------------------------------------
            # Atmosphere
            # ------------------------------------------------

            density = values[i]

            i += 1

            pressure = values[i]

            i += 1

            temperature = values[i]

            i += 1

            # ------------------------------------------------
            # ECI -> geographic coordinates
            # ------------------------------------------------

            latitude, longitude, altitude = (
                eci_to_geodetic(
                    px,
                    py,
                    pz,
                    sim_time
                )
            )

            # ------------------------------------------------
            # Orbital analysis
            # ------------------------------------------------

            radius = math.sqrt(
                px * px +
                py * py +
                pz * pz
            )

            velocity = math.sqrt(
                vx * vx +
                vy * vy +
                vz * vz
            )

            drag_force = math.sqrt(
                drag_x * drag_x +
                drag_y * drag_y +
                drag_z * drag_z
            )

            # ------------------------------------------------
            # CSV
            # ------------------------------------------------

            telemetry_writer.writerow([
                sim_time,

                px,
                py,
                pz,

                vx,
                vy,
                vz,

                qw,
                qx,
                qy,
                qz,

                drag_x,
                drag_y,
                drag_z,

                density,
                pressure,
                temperature,

                latitude,
                longitude,
                altitude
            ])

            telemetry_file.flush()

            # ------------------------------------------------
            # Unity packet
            #
            # Keep the existing 88-byte format.
            #
            # 11 doubles:
            #
            #   sim_time
            #   px py pz
            #   qw qx qy qz
            #   latitude longitude altitude
            #
            # Atmospheric data is intentionally NOT added
            # to this packet so TrickReceiver.cs does not need
            # to change.
            # ------------------------------------------------

            packet = struct.pack(
                "<11d",
                sim_time,
                px,
                py,
                pz,
                qw,
                qx,
                qy,
                qz,
                latitude,
                longitude,
                altitude
            )

            # ------------------------------------------------
            # Send to Unity
            # ------------------------------------------------

            try:

                unity_sock.sendto(
                    packet,
                    (
                        UNITY_HOST,
                        UNITY_PORT
                    )
                )

                packet_count += 1

            except OSError as e:

                print(
                    f"[bridge] UDP send error: {e}"
                )

                break

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            current_time = time.time()

            if (
                current_time -
                last_print_time >= 1.0
            ):

                print(
                    f"[bridge] "
                    f"Packets={packet_count:6d} | "
                    f"t={sim_time:8.1f} s | "
                    f"Lat={latitude:8.3f}° | "
                    f"Lon={longitude:9.3f}° | "
                    f"Alt={altitude / 1000.0:8.2f} km | "
                    f"Vel={velocity / 1000.0:7.3f} km/s | "
                    f"Drag={drag_force:10.3e} N | "
                    f"Density={density:10.3e} kg/m³ | "
                    f"Temp={temperature:8.2f} K"
                )

                last_print_time = current_time

    finally:

        # ====================================================
        # Cleanup
        # ====================================================

        print(
            "[bridge] Closing telemetry file..."
        )

        telemetry_file.close()

        trick_sock.close()

        unity_sock.close()

        print(
            "[bridge] Bridge stopped."
        )


if __name__ == "__main__":

    main()