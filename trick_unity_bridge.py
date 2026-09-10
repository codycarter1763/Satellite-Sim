#!/usr/bin/env python3

import argparse
import csv
import math
import socket
import struct
import time

TRICK_HOST = "localhost"
UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005

CYCLE_SEC = 0.10

EARTH_RATE = 7.2921151467e-5
EARTH_RADIUS = 6371000.0

TRICK_BROADCAST_ADDR = "224.3.14.15"
TRICK_BROADCAST_PORT = 9265

VEHICLE = "vehicle"

VARS = [
    "time",
    f"{VEHICLE}.dyn_body.composite_body.state.trans.position[0]",           # ECI X position
    f"{VEHICLE}.dyn_body.composite_body.state.trans.position[1]",           # ECI Y position
    f"{VEHICLE}.dyn_body.composite_body.state.trans.position[2]",           # ECI Z position
    f"{VEHICLE}.dyn_body.composite_body.state.trans.velocity[0]",           # ECI X velocity
    f"{VEHICLE}.dyn_body.composite_body.state.trans.velocity[1]",           # ECI Y velocity
    f"{VEHICLE}.dyn_body.composite_body.state.trans.velocity[2]",           # ECI Z velocity
    f"{VEHICLE}.dyn_body.composite_body.state.rot.Q_parent_this.scalar",    # Quaternion scalar
    f"{VEHICLE}.dyn_body.composite_body.state.rot.Q_parent_this.vector[0]", # Quaternion vector X
    f"{VEHICLE}.dyn_body.composite_body.state.rot.Q_parent_this.vector[1]", # Quaternion vector Y
    f"{VEHICLE}.dyn_body.composite_body.state.rot.Q_parent_this.vector[2]", # Quaternion vector Z
]


"""Converts Earth-Centered Inertial (ECI) coordinates to geodetic coordinates (latitude, longitude, altitude) for the ground map."""
def eci_to_geodetic(x, y, z, t):
    angle = EARTH_RATE * t
    c = math.cos(angle)
    s = math.sin(angle)

    xe = c * x + s * y
    ye = -s * x + c * y

    lon = math.degrees(math.atan2(ye, xe))
    lat = math.degrees(math.atan2(z, math.sqrt(xe * xe + ye * ye)))
    alt = math.sqrt(x * x + y * y + z * z) - EARTH_RADIUS

    return lat, lon, alt

"""Finds a running Trick simulation on the local network and returns host and port"""
def discover_trick(match, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", TRICK_BROADCAST_PORT))

    group = struct.pack(
        "4sl",
        socket.inet_aton(TRICK_BROADCAST_ADDR),
        socket.INADDR_ANY,
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group)
    sock.settimeout(timeout)

    print("Waiting for Trick...")

    end = time.time() + timeout

    while time.time() < end:
        try:
            data, _ = sock.recvfrom(2048)
            fields = data.decode(errors="replace").split("\t")

            if len(fields) < 10:
                continue

            info = {
                "host": fields[0],
                "port": int(fields[1]),
                "dir": fields[4],
                "input": fields[6],
                "main": fields[5],
            }

            text = f"{info['dir']} {info['input']} {info['main']}"

            if match is None or match in text:
                sock.close()
                print(f"Found Trick on {info['host']}:{info['port']}")
                return info["host"], info["port"]

        except (socket.timeout, ValueError, OSError):
            break

    sock.close()
    raise RuntimeError("No Trick simulation found.")

"""Connects to a Trick simulation at the given host and port."""
def connect_trick(host, port):
    for _ in range(50):
        try:
            sock = socket.create_connection((host, port), timeout=2)
            print(f"Connected to Trick at {host}:{port}")
            return sock
        except OSError:
            time.sleep(0.2)

    raise RuntimeError("Could not connect to Trick.")

"""Helper to send a command to Trick over the socket."""
def send(sock, command):
    sock.sendall((command + "\n").encode())

"""Helper to receive a line of text from Trick over the socket."""
def receive_line(sock, buffer):
    while b"\n" not in buffer:
        data = sock.recv(4096)

        if not data:
            raise ConnectionError("Trick closed the connection.")

        buffer += data

    line, _, buffer = buffer.partition(b"\n")
    return line.decode().strip(), buffer

"""Main function to bridge Trick telemetry data to Unity."""
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int)
    parser.add_argument("--port", dest="port_option", type=int)
    parser.add_argument("--host", default=TRICK_HOST)
    parser.add_argument("--match")
    args = parser.parse_args()

    if args.port_option is not None:
        port = args.port_option
    else:
        port = args.port

    if port is None:
        host, port = discover_trick(args.match, 30)
    else:
        host = args.host

    trick = connect_trick(host, port)
    unity = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        for var in VARS:                                # Requests Trick to send the specified variables
            send(trick, f'trick.var_add("{var}")')

        send(trick, f"trick.var_cycle({CYCLE_SEC})")    # Requests Trick to send the variables at the specified cycle time
        send(trick, "trick.var_send()")                 # Requests Trick to send the variables immediately

        print(f"Sending Unity data to {UNITY_HOST}:{UNITY_PORT}")

        buffer = b""
        packets = 0

        while True:
            line, buffer = receive_line(trick, buffer)
            parts = line.split()

            if len(parts) < 3 or parts[0] != "0":
                continue

            try:
                sim_time = float(parts[1])
                values = [float(x) for x in parts[3:]]
            except ValueError:
                continue

            if len(values) != 10:
                continue

            px, py, pz = values[0:3] # Position in ECI coordinates from Trick
            vx, vy, vz = values[3:6] # Velocity in ECI coordinates from Trick
            qw, qx, qy, qz = values[6:10] # Quaternion representing orientation for Unity

            lat, lon, alt = eci_to_geodetic(px, py, pz, sim_time) # Converts ECI coordinates to geodetic coordinates for Unity ground track

            packet = struct.pack(
                "<11d",
                sim_time,
                px, py, pz,
                qw, qx, qy, qz,
                lat, lon, alt
            )

            unity.sendto(packet, (UNITY_HOST, UNITY_PORT))
            packets += 1

            if packets % 10 == 0:
                speed = math.sqrt(vx * vx + vy * vy + vz * vz)
                print(
                    f"Packets={packets} "
                    f"Time={sim_time:.1f}s "
                    f"Alt={alt / 1000:.2f}km "
                    f"Speed={speed / 1000:.3f}km/s"
                )

    except KeyboardInterrupt:
        print("\nStopping bridge.")

    finally:
        trick.close()
        unity.close()


if __name__ == "__main__":
    main()
