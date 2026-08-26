import socket
import struct
import time
import math

HOST = "127.0.0.1"
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Sending UDP packets to {HOST}:{PORT}")

t = 0.0
dt = 0.1

try:
    while True:
        # Simulated motion:
        # x starts at 10 m and moves at -2 m/s
        x = 10.0 - 2.0 * t
        y = 0.0
        z = 0.0

        vx = -2.0
        vy = 0.0
        vz = 0.0

        # Must exactly match Unity's expected layout:
        # double time
        # double position[3]
        # double velocity[3]
        packet = struct.pack(
            "<7d",
            t,
            x, y, z,
            vx, vy, vz
        )

        sock.sendto(packet, (HOST, PORT))

        print(
            f"t={t:6.2f}  "
            f"pos=({x:7.2f}, {y:5.2f}, {z:5.2f})  "
            f"vel=({vx:5.2f}, {vy:5.2f}, {vz:5.2f})"
        )

        t += dt
        time.sleep(dt)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    sock.close()