#---------------------------------------------
# Set up Trick executive parameters.
#---------------------------------------------

trick.var_server_set_enabled(1)


#---------------------------------------------
# Data recording
#---------------------------------------------

exec(open("Modified_data/realtime.py").read())

exec(compile(
    open("Log_data/log_state.py", "rb").read(),
    "Log_data/log_state.py",
    "exec"
))

log_state(1.0, "vehicle")
log_state(1.0, "vehicle2")


#---------------------------------------------
# Dynamics manager
#---------------------------------------------

dynamics.dyn_manager_init.mode = \
    trick.DynManagerInit.EphemerisMode_EmptySpace

dynamics.dyn_manager_init.central_point_name = "Space"

rk_integrator = trick.RK4IntegratorConstructor()
dynamics.dyn_manager_init.integ_constructor = rk_integrator


#---------------------------------------------
# Vehicle 1
#---------------------------------------------

vehicle.dyn_body.set_name("veh")
vehicle.dyn_body.integ_frame_name = "Space.inertial"
vehicle.dyn_body.translational_dynamics = True
vehicle.dyn_body.rotational_dynamics = True


#---------------------------------------------
# Vehicle 2
#---------------------------------------------

vehicle2.dyn_body.set_name("veh2")
vehicle2.dyn_body.integ_frame_name = "Space.inertial"
vehicle2.dyn_body.translational_dynamics = True
vehicle2.dyn_body.rotational_dynamics = True


#---------------------------------------------
# Mass properties
#---------------------------------------------

exec(compile(
    open("Modified_data/vehicle_mass_props.py", "rb").read(),
    "vehicle_mass_props.py",
    "exec"
))

set_mass_props(vehicle)
set_mass_props(vehicle2)


#---------------------------------------------
# State initialization
#---------------------------------------------

exec(compile(
    open("Modified_data/vehicle_state.py", "rb").read(),
    "vehicle_state.py",
    "exec"
))


# Vehicle 1
set_state(
    vehicle,
    [10, 0, 0],
    [-2, 0, 0],
    180.0,
    [0.0, 0.0, 1.0],
    [0.0, 0.0, -36.0]
)


# Vehicle 2
set_state(
    vehicle2,
    [0, 0, 0],
    [0, 0, 0],
    0.0,
    [0.0, 0.0, 1.0],
    [0.0, 0.0, 0.0]
)


#---------------------------------------------
# Add body initialization actions
#---------------------------------------------

dynamics.dyn_manager.add_body_action(vehicle.mass_init)
dynamics.dyn_manager.add_body_action(vehicle.trans_init)
dynamics.dyn_manager.add_body_action(vehicle.rot_init)

dynamics.dyn_manager.add_body_action(vehicle2.mass_init)
dynamics.dyn_manager.add_body_action(vehicle2.trans_init)
dynamics.dyn_manager.add_body_action(vehicle2.rot_init)


#---------------------------------------------
# Termination
#---------------------------------------------

trick.sim_services.exec_set_terminate_time(10.0)


#---------------------------------------------
# Start Unity Variable Server bridge
#---------------------------------------------

import os

varServerPort = trick.var_server_get_port()

bridge_path = os.path.join(
    os.getcwd(),
    "trick_unity_bridge.py"
)

print("=============================================")
print("Unity Bridge Setup")
print("=============================================")
print("Current directory:", os.getcwd())
print("Variable Server port:", varServerPort)
print("Bridge path:", bridge_path)
print("Bridge exists:", os.path.isfile(bridge_path))


if os.path.isfile(bridge_path):

    bridge_cmd = (
        f"python3 -u {bridge_path} "
        f"{varServerPort}"
    )

    print("Starting Unity bridge:")
    print(bridge_cmd)

    os.system(
        bridge_cmd +
        " > unity_bridge.log 2>&1 &"
    )

else:

    print(
        "ERROR: Cannot find Unity bridge:"
    )

    print(bridge_path)