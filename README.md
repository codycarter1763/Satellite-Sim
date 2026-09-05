# NASA Trick & JEOD & Unity Satellite Dynamics Simulation

<img width="2559" height="1403" alt="Screenshot from 2026-09-04 00-03-39" src="https://github.com/user-attachments/assets/ba896282-6f78-4a18-9ed1-bc9809b483ba" />

# About
This repository builds on my NASA Trick simulation learning journey through a satellite dynamics simulation. 

The project ties together three distinct systems:

- **NASA Trick Simulation** — physics simulation and job scheduling
- **NASA JEOD** — Orbital dynamics package for Trick
- **Unity Graphics** — Simulation visualization for real time analysis

Feel free to clone the repo and run your own tests!


# What is NASA Trick?
<img width="1899" height="621" alt="image" src="https://github.com/user-attachments/assets/ab2f4180-cadc-4fb6-9af9-0095222f9737" />

The Trick Simulation Environment is a physics framework developed at the NASA Johnson Space Center and is used to develop and design space vehicles. Trick provides tools for quickly simulating designs and allows for realtime synchronization, job scheduling, checkpoints, data recording and logging, and a input processor. Essentially, Trick gives you the tools needed so engineers can quickly model and simulate their designs without having to create a simulation from scratch for each design aspect. 

For NASA, this allowed them to apply this framework to numerous projects, including the Systems Engineering Simulator and Virtual Reality lab for training astronauts.

Read up on more information about Trick [here](https://github.com/nasa/trick?tab=readme-ov-file).

# What is NASA JEOD?
NASA JEOD (JSC Engineering Orbital Dynamics) is a simulation framework developed at
NASA's Johnson Space Center for modeling the orbital and rotational dynamics of
spacecraft and other space vehicles. 

For this project, JEOD is responsible for the spacecraft's orbital dynamics while
Trick provides the simulation framework and execution environment. 

More information about JEOD can be found in the
[JEOD repository](https://github.com/nasa/jeod).

# Unity Engine
To better visualize how the satellite orbits Earth, Trick data is passed to Unity and runs in real time as the simulation runs. The UI includes models of Earth, a 3D model of NASA GOES satellite, and a map with a trail showing where the satellite has traveled. This allows Trick to be tailored with different parameters to be able to show differences in satellite orbit.

# Simulation Architecture
This project combines NASA Trick, NASA JEOD, Python, and Unity into a single
spacecraft simulation and visualization pipeline. 

## Flow

## Simulation Physics

JEOD provides many physics models. Currently, the following are implemented in this spacecraft simulation to add real-word variables:

| Physics / Model | Description |
|---|---|
| **Orbital Dynamics** | Spacecraft position and velocity are propagated about Earth. |
| **Earth Gravity** | Non-spherical Earth gravity using the JEOD GGM05C gravity model. |
| **Spacecraft Mass Properties** | Simplified 500 kg spacecraft mass and defined inertia properties. |
| **Rotational Dynamics** | Spacecraft attitude and angular velocity are propagated using JEOD rotational dynamics. |
| **Atmospheric Model** | Atmospheric density, pressure, and temperature are modeled at the spacecraft's location. |
| **Aerodynamic Drag** | Atmospheric drag is calculated using a rectangular spacecraft. |
| **LVLH Reference Frame** | A reference frame follows the spacecraft for future GNC development. |

# Testing
In this repo, I included various tools to help visualize and plot simulation data, whether that be through Unity or log_state files. I'll show some important trends below as examples:

## Spacecraft Orbital Path

<img width="1050" height="832" alt="image" src="https://github.com/user-attachments/assets/d8d59509-c529-4d6c-be4f-20824c654789" />

<img width="2106" height="511" alt="image" src="https://github.com/user-attachments/assets/205d7b1b-cfbf-4f22-87d9-3ed785969c2a" />

## Altitude 
<img width="1817" height="512" alt="image" src="https://github.com/user-attachments/assets/fba6444f-96b1-4b5f-97c7-467d9bcafd71" />


## Atmospheric Density vs. Altitude
<img width="1380" height="508" alt="image" src="https://github.com/user-attachments/assets/e2cac0d8-9e30-407b-84d7-feb358d9147f" />


## Drag Force vs. Atmospheric Density

## Ground Track


# Conclusion
