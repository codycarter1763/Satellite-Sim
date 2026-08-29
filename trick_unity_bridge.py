#!/usr/bin/env python3

import sys
import socket
import struct


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

UNITY_HOST = "127.0.0.1"
UNITY_PORT = 5005

BODIES = ["vehicle", "vehicle2"]


# ------------------------------------------------------------
# Build Variable Server variable list
# ------------------------------------------------------------

def body_vars(body_name):

    base = f"{body_name}.dyn_body.composite_body.state"

    varlist = [
        f"{base}.trans.position[0]",
        f"{base}.trans.position[1]",
        f"{base}.trans.position[2]",
    ]

    for i in range(3):
        for j in range(3):
            varlist.append(
                f"{base}.rot.T_parent_this[{i}][{j}]"
            )

    return varlist


ALL_VARS = []

for body in BODIES:
    ALL_VARS.extend(body_vars(body))


# Each body:
#   3 position
#   9 DCM
# = 12 values

VARS_PER_BODY = 12
NUM_VALUES = len(ALL_VARS)


# ------------------------------------------------------------
# DCM -> quaternion
# ------------------------------------------------------------

def dcm_to_quaternion(T):

    trace = (
        T[0][0]
        + T[1][1]
        + T[2][2]
    )

    if trace > 0:

        s = 0.5 / (trace + 1.0) ** 0.5

        w = 0.25 / s
        x = (T[2][1] - T[1][2]) * s
        y = (T[0][2] - T[2][0]) * s
        z = (T[1][0] - T[0][1]) * s

    elif T[0][0] > T[1][1] and T[0][0] > T[2][2]:

        s = 2.0 * (
            1.0
            + T[0][0]
            - T[1][1]
            - T[2][2]
        ) ** 0.5

        w = (T[2][1] - T[1][2]) / s
        x = 0.25 * s
        y = (T[0][1] + T[1][0]) / s
        z = (T[0][2] + T[2][0]) / s

    elif T[1][1] > T[2][2]:

        s = 2.0 * (
            1.0
            + T[1][1]
            - T[0][0]
            - T[2][2]
        ) ** 0.5

        w = (T[0][2] - T[2][0]) / s
        x = (T[0][1] + T[1][0]) / s
        y = 0.25 * s
        z = (T[1][2] + T[2][1]) / s

    else:

        s = 2.0 * (
            1.0
            + T[2][2]
            - T[0][0]
            - T[1][1]
        ) ** 0.5

        w = (T[1][0] - T[0][1]) / s
        x = (T[0][2] + T[2][0]) / s
        y = (T[1][2] + T[2][1]) / s
        z = 0.25 * s

    return w, x, y, z


# ------------------------------------------------------------
# JEOD -> Unity coordinate conversion
# ------------------------------------------------------------

def jeod_to_unity_position(x, y, z):
    return x, z, y


def jeod_to_unity_quaternion(w, x, y, z):
    return w, x, z, y


# ------------------------------------------------------------
# Command line
# ------------------------------------------------------------

if len(sys.argv) != 2:

    print(
        "Usage: trick_unity_bridge.py "
        "<trick_variable_server_port>"
    )

    sys.exit(1)


trick_port = int(sys.argv[1])


# ------------------------------------------------------------
# Connect to Trick Variable Server
# ------------------------------------------------------------

print(
    f"Connecting to Trick Variable Server "
    f"localhost:{trick_port}",
    flush=True
)

trick_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

try:

    trick_socket.connect(
        ("localhost", trick_port)
    )

except Exception as e:

    print(
        f"Could not connect to Trick: {e}",
        flush=True
    )

    sys.exit(1)


print(
    "Connected to Trick Variable Server.",
    flush=True
)

trick_input = trick_socket.makefile("r")


# ------------------------------------------------------------
# Unity UDP socket
# ------------------------------------------------------------

unity_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

print(
    f"Unity UDP socket ready: "
    f"{UNITY_HOST}:{UNITY_PORT}",
    flush=True
)


# ------------------------------------------------------------
# Configure Trick Variable Server
# ------------------------------------------------------------

commands = (
    "trick.var_pause()\n"
    "trick.var_ascii()\n"
    "trick.var_clear()\n"
)

for var in ALL_VARS:

    commands += (
        f'trick.var_add("{var}")\n'
    )

commands += (
    "trick.var_cycle(0.005)\n"
    "trick.var_unpause()\n"
)

print(
    "Sending Variable Server configuration...",
    flush=True
)

trick_socket.sendall(
    commands.encode("ascii")
)

print(
    "Trick Variable Server configured.",
    flush=True
)

print(
    f"Bodies: {BODIES}",
    flush=True
)

print(
    f"Variables requested: {NUM_VALUES}",
    flush=True
)


# ------------------------------------------------------------
# Receive data
# ------------------------------------------------------------

try:

    while True:

        line = trick_input.readline()

        if line == "":

            print(
                "Trick Variable Server closed connection.",
                flush=True
            )

            break

        line = line.strip()

        if not line:
            continue


        fields = line.split("\t")


        # ----------------------------------------------------
        # Message type
        # ----------------------------------------------------

        if fields[0] != "0":
            continue


        # ----------------------------------------------------
        # Expected message layout
        #
        # fields[0] = Trick message type
        # fields[1:] = 24 spacecraft values
        #
        # 12 vehicle
        # 12 vehicle2
        #
        # Total = 25 fields
        # ----------------------------------------------------

        if len(fields) < NUM_VALUES + 1:

            print(
                f"Not enough fields: "
                f"{len(fields)} "
                f"(expected at least {NUM_VALUES + 1})",
                flush=True
            )

            continue


        try:

            values = [
                float(f)
                for f in fields[1:NUM_VALUES + 1]
            ]

        except ValueError as e:

            print(
                f"Could not convert values: {e}",
                flush=True
            )

            continue


        # ----------------------------------------------------
        # Build Unity packet
        # ----------------------------------------------------

        packet_values = []


        # ----------------------------------------------------
        # Process each body
        # ----------------------------------------------------

        for b, body in enumerate(BODIES):

            offset = b * VARS_PER_BODY


            # ------------------------------------------------
            # Position
            # ------------------------------------------------

            px = values[offset + 0]
            py = values[offset + 1]
            pz = values[offset + 2]


            # ------------------------------------------------
            # DCM
            # ------------------------------------------------

            dcm_flat = values[
                offset + 3:
                offset + 12
            ]

            T = [
                dcm_flat[0:3],
                dcm_flat[3:6],
                dcm_flat[6:9]
            ]


            # ------------------------------------------------
            # DCM -> quaternion
            # ------------------------------------------------

            qw, qx, qy, qz = \
                dcm_to_quaternion(T)


            # ------------------------------------------------
            # JEOD -> Unity
            # ------------------------------------------------

            ux, uy, uz = \
                jeod_to_unity_position(
                    px,
                    py,
                    pz
                )

            uqw, uqx, uqy, uqz = \
                jeod_to_unity_quaternion(
                    qw,
                    qx,
                    qy,
                    qz
                )


            # ------------------------------------------------
            # Add body state
            # ------------------------------------------------

            packet_values.extend([
                ux,
                uy,
                uz,
                uqw,
                uqx,
                uqy,
                uqz
            ])


            # ------------------------------------------------
            # Debug output
            # ------------------------------------------------

            print(
                f"{body}: "
                f"pos=("
                f"{ux:.3f}, "
                f"{uy:.3f}, "
                f"{uz:.3f}) "
                f"quat=("
                f"{uqw:.3f}, "
                f"{uqx:.3f}, "
                f"{uqy:.3f}, "
                f"{uqz:.3f})",
                flush=True
            )


        # ----------------------------------------------------
        # Send to Unity
        # ----------------------------------------------------

        # 2 bodies
        #
        # Each body:
        #   3 position
        #   4 quaternion
        #
        # 7 values per body
        # 14 doubles total
        #
        # 14 * 8 = 112 bytes

        packet = struct.pack(
            "<14d",
            *packet_values
        )

        unity_socket.sendto(
            packet,
            (
                UNITY_HOST,
                UNITY_PORT
            )
        )


except ConnectionResetError:

    print(
        "Trick Variable Server reset the connection.",
        flush=True
    )


except BrokenPipeError:

    print(
        "Trick Variable Server connection closed.",
        flush=True
    )


except KeyboardInterrupt:

    print(
        "\nBridge stopped.",
        flush=True
    )


finally:

    try:
        trick_socket.close()
    except Exception:
        pass

    try:
        unity_socket.close()
    except Exception:
        pass

    print(
        "Bridge shutdown.",
        flush=True
    )