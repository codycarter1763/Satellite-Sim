#---------------------------------------------
# Set up Trick executive parameters.
#---------------------------------------------
#trick.sim_services.exec_set_trap_sigfpe(1)

from Modified_data.vehicle_grav_controls_non_spherical import veh_grav_controls


trick.var_server_set_enabled(1)
#exec(open("Modified_data/realtime.py").read())

#---------------------------------------------
# Set Up Data Recording
#---------------------------------------------
exec(compile(open("Log_data/log_state.py", "rb").read(),
             "Log_data/log_state.py", 'exec'))
trick.var_cycle(0.1)
log_state(1.0)


#---------------------------------------------
# Configure Dynamics Manager
#---------------------------------------------
dynamics.dyn_manager_init.mode = trick.DynManagerInit.EphemerisMode_SinglePlanet
dynamics.dyn_manager_init.central_point_name = "Earth"

rk_integrator = trick.RK4IntegratorConstructor()
dynamics.dyn_manager_init.integ_constructor = rk_integrator


#---------------------------------------------
# Configure Vehicle
#---------------------------------------------
vehicle.dyn_body.set_name("vehicle")
vehicle.dyn_body.integ_frame_name = "Earth.inertial"
vehicle.dyn_body.translational_dynamics = True
vehicle.dyn_body.rotational_dynamics = True

vehicle.lvlh_frame.set_subject_name("vehicle.composite_body")
vehicle.lvlh_frame.set_planet_name("Earth")

#---------------------------------------------
# Vehicle configuration
#---------------------------------------------
exec(compile(open("Modified_data/time.py", "rb").read(),
             "Modified_data/time.py", 'exec'))

exec(compile(open("Modified_data/vehicle_mass_props.py", "rb").read(),
             "Modified_data/vehicle_mass_props.py", 'exec'))

exec(compile(open("Modified_data/vehicle_state.py", "rb").read(),
             "Modified_data/vehicle_state.py", 'exec'))

exec(compile(open("Modified_data/vehicle_grav_controls_non_spherical.py", "rb").read(),
             "Modified_data/vehicle_grav_controls_non_spherical.py", 'exec'))

exec(compile(open("Modified_data/surface.py", "rb").read(),
             "Modified_data/surface.py", 'exec'))

veh_grav_controls(200, 200)


dynamics.dyn_manager.add_body_action(vehicle.mass_init)
dynamics.dyn_manager.add_body_action(vehicle.trans_init)
dynamics.dyn_manager.add_body_action(vehicle.rot_init)

#---------------------------------------------
# Configure Planet Fixed Frame
#---------------------------------------------
vehicle.pfix.reference_name = "Earth"

#---------------------------------------------
# Simulation Termination
#---------------------------------------------
trick.sim_services.exec_set_terminate_time(86400.0)


#---------------------------------------------
# Configure Aerodynamic Drag
#---------------------------------------------
interactions.aero_drag.active = True
interactions.aero_drag.use_default_behavior = False
interactions.aero_drag.set_aero_surface(interactions.aero_surface)

interactions.aero_drag.param.gas_const = 287
interactions.aero_drag.param.temp_free_stream = 1487

#---------------------------------------------
# Start Unity Variable Server Bridge
#---------------------------------------------
import os

varServerPort = trick.var_server_get_port()
bridge_path = os.path.join(os.getcwd(), "trick_unity_bridge.py")

print("=============================================")
print("Unity Bridge Setup")
print("=============================================")
print("Current directory:", os.getcwd())
print("Variable Server port:", varServerPort)
print("Bridge path:", bridge_path)
print("Bridge exists:", os.path.isfile(bridge_path))

if os.path.isfile(bridge_path):
    bridge_cmd = f"python3 -u {bridge_path} {varServerPort}"

    print("Starting Unity bridge:")
    print(bridge_cmd)

    os.system(bridge_cmd + " > unity_bridge.log 2>&1 &")

else:
    print("ERROR: Cannot find Unity bridge:")
    print(bridge_path)