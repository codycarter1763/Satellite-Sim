#!/usr/bin/env python3

import sys
import socket
import struct


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005


POSITION_X = \
    "vehicle.dyn_body.composite_body.state.trans.position[0]"

POSITION_Y = \
    "vehicle.dyn_body.composite_body.state.trans.position[1]"

POSITION_Z = \
    "vehicle.dyn_body.composite_body.state.trans.position[2]"


# ------------------------------------------------------------
# Get Trick Variable Server port
# ------------------------------------------------------------

if len(sys.argv) != 2:
    print("Usage:")
    print("  trick_unity_bridge.py <trick_variable_server_port>")
    sys.exit(1)

trick_port = int(sys.argv[1])


# ------------------------------------------------------------
# Connect to Trick Variable Server
# ------------------------------------------------------------

print(
    f"Connecting to Trick Variable Server "
    f"localhost:{trick_port}"
)

trick_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

try:
    trick_socket.connect(("localhost", trick_port))
except ConnectionRefusedError:
    print("Could not connect to Trick Variable Server.")
    sys.exit(1)


print("Connected to Trick Variable Server.")


# Convert socket into a text file for readline()
trick_input = trick_socket.makefile("r")


# ------------------------------------------------------------
# Connect to Unity
# ------------------------------------------------------------

print(
    f"Connecting to Unity UDP "
    f"{UNITY_HOST}:{UNITY_PORT}"
)

unity_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

print("Unity UDP socket ready.")


# ------------------------------------------------------------
# Configure Trick Variable Server
# ------------------------------------------------------------

commands = (
    "trick.var_pause()\n"
    "trick.var_ascii()\n"

    f"trick.var_clear()\n"

    f"trick.var_add(\"{POSITION_X}\")\n"
    f"trick.var_add(\"{POSITION_Y}\")\n"
    f"trick.var_add(\"{POSITION_Z}\")\n"

    "trick.var_cycle(0.01)\n"
    "trick.var_unpause()\n"
)

trick_socket.sendall(commands.encode("ascii"))

print("Trick Variable Server configured.")
print("Streaming position data to Unity...")


# ------------------------------------------------------------
# Receive Trick data and forward to Unity
# ------------------------------------------------------------

try:

    while True:

        line = trick_input.readline()

        if line == "":
            print("Trick Variable Server disconnected.")
            break

        line = line.strip()

        if not line:
            continue

        # Trick ASCII format:
        #
        # 0<TAB>x<TAB>y<TAB>z
        #
        fields = line.split("\t")

        if len(fields) < 4:
            continue

        # Message type 0 = variable list
        if fields[0] != "0":
            continue

        try:
            x = float(fields[1])
            y = float(fields[2])
            z = float(fields[3])

        except ValueError:
            continue

        print(
            f"Position: "
            f"x={x:.3f}, "
            f"y={y:.3f}, "
            f"z={z:.3f}"
        )

        # ----------------------------------------------------
        # Send the same simple format to Unity:
        #
        # double x
        # double y
        # double z
        #
        # 24 bytes
        # ----------------------------------------------------

        packet = struct.pack(
            "<3d",
            x,
            y,
            z
        )

        unity_socket.sendto(
            packet,
            (UNITY_HOST, UNITY_PORT)
        )


except KeyboardInterrupt:

    print("\nBridge stopped.")


finally:

    try:
        trick_socket.sendall(
            b"trick.var_pause()\n"
        )
    except Exception:
        pass

    trick_input.close()
    trick_socket.close()
    unity_socket.close()