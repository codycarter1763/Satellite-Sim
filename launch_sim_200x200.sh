#!/bin/bash

cd "$(dirname "$0")"

echo "Starting Trick/JEOD..."

./S_main_Linux_11.4_x86_64.exe SET_test/RUN_test/RUN_200x200/input.py &
TRICK_PID=$!

sleep 3

echo "Starting Unity..."

cd Unity_Orbit
./"Satellite UI.x86_64" &
UNITY_PID=$!

trap 'kill $UNITY_PID $TRICK_PID 2>/dev/null' EXIT INT TERM

echo "Simulation running."
echo "Press Ctrl+C to stop."

wait $TRICK_PID