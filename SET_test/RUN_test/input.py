#---------------------------------------------
# Set up Trick executive parameters.
#---------------------------------------------
#trick.sim_services.exec_set_trap_sigfpe(1)

trick.var_server_set_enabled(1)
exec(open("Modified_data/realtime.py").read())

# Set Up Data Recording
exec(compile(open("Log_data/log_state.py", "rb").read(),
             "Log_data/log_state.py", 'exec'))
log_state(1.0, "vehicle")

# Configure the dynamics manager to operate in single-planet mode
dynamics.dyn_manager_init.mode = trick.DynManagerInit.EphemerisMode_SinglePlanet
dynamics.dyn_manager_init.central_point_name = "Earth"

rk_integrator = trick.RK4IntegratorConstructor()
dynamics.dyn_manager_init.integ_constructor = rk_integrator

vehicle.dyn_body.set_name("veh")
vehicle.dyn_body.integ_frame_name = "Earth.inertial"
vehicle.dyn_body.translational_dynamics = True
vehicle.dyn_body.rotational_dynamics = True

exec(compile(open("Modified_data/vehicle_mass_props.py", "rb").read(),
             "Modified_data/vehicle_mass_props.py", 'exec'))

exec(compile(open("Modified_data/vehicle_state.py", "rb").read(),
             "Modified_data/vehicle_state.py", 'exec'))

exec(compile(open("Modified_data/vehicle_grav_controls.py", "rb").read(),
             "Modified_data/vehicle_grav_controls.py", 'exec'))

dynamics.dyn_manager.add_body_action( vehicle.mass_init )
dynamics.dyn_manager.add_body_action( vehicle.trans_init )
dynamics.dyn_manager.add_body_action( vehicle.rot_init )

trick.sim_services.exec_set_terminate_time(18000.0)

#---------------------------------------------
# Start Unity Variable Server bridge
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