#!/usr/bin/env python3

import argparse
import math
import socket
import struct
import sys
import time


# ============================================================
# Configuration
# ============================================================

TRICK_HOST = "localhost"

UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005

CYCLE_SEC = 0.10

VEHICLE_NAME = "vehicle"

# Earth rotation rate [rad/s]
EARTH_ROTATION_RATE = 7.2921151467e-5

# Earth mean radius [m]
EARTH_RADIUS = 6_371_000.0

# Initial Greenwich angle.
#
# This determines where longitude 0 is at simulation time = 0.
# For a demo, zero is perfectly fine.
INITIAL_EARTH_ROTATION = 0.0

# Trick variable server broadcast channel
TRICK_BROADCAST_ADDR = "224.3.14.15"
TRICK_BROADCAST_PORT = 9265


# ============================================================
# Trick variables
# ============================================================

TRICK_VARS = [
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[0]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[1]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.trans.position[2]",

    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.scalar",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[0]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[1]",
    f"{VEHICLE_NAME}.dyn_body.composite_body.state.rot.Q_parent_this.vector[2]",
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

    # ECI -> ECEF
    x_ecef = c * x + s * y
    y_ecef = -s * x + c * y
    z_ecef = z

    longitude = math.atan2(y_ecef, x_ecef)

    horizontal = math.sqrt(
        x_ecef * x_ecef +
        y_ecef * y_ecef
    )

    latitude = math.atan2(
        z_ecef,
        horizontal
    )

    radius = math.sqrt(
        x * x +
        y * y +
        z * z
    )

    altitude = radius - EARTH_RADIUS

    latitude_deg = math.degrees(latitude)
    longitude_deg = math.degrees(longitude)

    # Normalize longitude to [-180, 180]
    if longitude_deg > 180.0:
        longitude_deg -= 360.0

    if longitude_deg < -180.0:
        longitude_deg += 360.0

    return latitude_deg, longitude_deg, altitude


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
        socket.inet_aton(TRICK_BROADCAST_ADDR),
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

    # --------------------------------------------------------
    # Connect to Trick
    # --------------------------------------------------------

    trick_sock = connect_trick(
        trick_host,
        trick_port
    )

    # --------------------------------------------------------
    # Unity UDP socket
    # --------------------------------------------------------

    unity_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    print(
        f"[bridge] UDP output: "
        f"{UNITY_HOST}:{UNITY_PORT}"
    )

    # --------------------------------------------------------
    # Subscribe
    # --------------------------------------------------------

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

    trick_send(
        trick_sock,
        f"trick.var_cycle({CYCLE_SEC})"
    )

    trick_send(
        trick_sock,
        "trick.var_send()"
    )

    # --------------------------------------------------------
    # Receive
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # Parse
        # ----------------------------------------------------

        parts = line.split()

        if len(parts) < 8:
            continue

        try:

            values = [
                float(p)
                for p in parts[1:8]
            ]

        except ValueError:

            continue

        # ----------------------------------------------------
        # Position
        # ----------------------------------------------------

        px = values[0]
        py = values[1]
        pz = values[2]

        # ----------------------------------------------------
        # Quaternion
        # ----------------------------------------------------

        qw = values[3]
        qx = values[4]
        qy = values[5]
        qz = values[6]

        # ----------------------------------------------------
        # Simulation time
        #
        # Trick sends the simulation time as the first
        # field in the variable-server response.
        # ----------------------------------------------------

        try:

            sim_time = float(parts[0])

        except ValueError:

            continue

        # ----------------------------------------------------
        # ECI -> geographic coordinates
        # ----------------------------------------------------

        latitude, longitude, altitude = (
            eci_to_geodetic(
                px,
                py,
                pz,
                sim_time
            )
        )

        # ----------------------------------------------------
        # Packet
        #
        # 11 doubles:
        #
        # 0  simulation time
        # 1  X
        # 2  Y
        # 3  Z
        # 4  Qw
        # 5  Qx
        # 6  Qy
        # 7  Qz
        # 8  latitude
        # 9  longitude
        # 10 altitude
        #
        # 11 * 8 = 88 bytes
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Send to Unity
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        current_time = time.time()

        if (
            current_time -
            last_print_time >= 1.0
        ):

            print(
                f"[bridge] Packets: "
                f"{packet_count:6d} | "
                f"Lat={latitude:8.3f}° | "
                f"Lon={longitude:9.3f}° | "
                f"Alt={altitude / 1000.0:8.2f} km"
            )

            last_print_time = current_time


if __name__ == "__main__":
    main()