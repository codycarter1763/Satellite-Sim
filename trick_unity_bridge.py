#!/usr/bin/env python3

import socket
import sys
import time
import struct


# ============================================================
# Configuration
# ============================================================

TRICK_HOST = "localhost"

UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005

CYCLE_SEC = 0.10

VEHICLE_NAME = "vehicle"


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
# Connect to Trick
# ============================================================

def connect_trick(port, retries=50, delay=0.2):

    for attempt in range(retries):

        try:

            s = socket.create_connection(
                (TRICK_HOST, port),
                timeout=2
            )

            print(
                f"[bridge] Connected to Trick variable server "
                f"on port {port}"
            )

            return s

        except (ConnectionRefusedError, OSError):

            time.sleep(delay)

    raise RuntimeError(
        f"[bridge] Could not connect to Trick variable server "
        f"on port {port}"
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
                "[bridge] Trick variable server closed connection"
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

    if len(sys.argv) < 2:

        print(
            "Usage: trick_unity_bridge.py "
            "<trick_var_server_port>"
        )

        sys.exit(1)


    trick_port = int(sys.argv[1])


    # ========================================================
    # Connect to Trick
    # ========================================================

    trick_sock = connect_trick(trick_port)


    # ========================================================
    # Create UDP socket for Unity
    # ========================================================

    unity_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    print(
        f"[bridge] UDP output: "
        f"{UNITY_HOST}:{UNITY_PORT}"
    )


    # ========================================================
    # Subscribe to Trick variables
    # ========================================================

    print("[bridge] Subscribing to variables...")

    for var in TRICK_VARS:

        print(f"[bridge]   {var}")

        trick_send(
            trick_sock,
            f'trick.var_add("{var}")'
        )


    # ========================================================
    # Configure Trick variable server
    # ========================================================

    trick_send(
        trick_sock,
        f"trick.var_cycle({CYCLE_SEC})"
    )

    trick_send(
        trick_sock,
        "trick.var_send()"
    )


    # ========================================================
    # Receive data
    # ========================================================

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


        # ====================================================
        # Show first raw Trick message
        # ====================================================

        if not first_line_shown:

            print()
            print(
                "================================================"
            )

            print(
                "[bridge] First raw Trick message:"
            )

            print(line)

            print(
                "================================================"
            )

            print()

            first_line_shown = True


        # ====================================================
        # Parse Trick data
        # ====================================================

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


        # ====================================================
        # Extract position
        # ====================================================

        px = values[0]
        py = values[1]
        pz = values[2]


        # ====================================================
        # Extract quaternion
        # ====================================================

        qw = values[3]
        qx = values[4]
        qy = values[5]
        qz = values[6]


        # ====================================================
        # Create binary packet
        # ====================================================

        packet = struct.pack(
            "<7d",
            px,
            py,
            pz,
            qw,
            qx,
            qy,
            qz
        )


        # ====================================================
        # Send UDP packet
        # ====================================================

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


        # ====================================================
        # Print status once per second
        # ====================================================

        current_time = time.time()

        if current_time - last_print_time >= 1.0:

            print(
                f"[bridge] Packets: {packet_count:6d} | "
                f"Position: "
                f"X={px:.3f} "
                f"Y={py:.3f} "
                f"Z={pz:.3f}"
            )

            print(
                f"[bridge] Quaternion: "
                f"W={qw:.6f} "
                f"X={qx:.6f} "
                f"Y={qy:.6f} "
                f"Z={qz:.6f}"
            )

            last_print_time = current_time

if __name__ == "__main__":
    main()