#---------------------------------------------
# Set up Trick executive parameters.
#---------------------------------------------
#trick.sim_services.exec_set_trap_sigfpe(1)

exec(compile(open("Log_data/log_state.py", "rb").read(),
             "Log_data/log_state.py", 'exec'))
log_state(1.0)

# Configure the dynamics manager to operate in empty space mode
dynamics.dyn_manager_init.mode = trick.DynManagerInit.EphemerisMode_EmptySpace
dynamics.dyn_manager_init.central_point_name = "Space"

rk_integrator = trick.RK4IntegratorConstructor()
dynamics.dyn_manager_init.integ_constructor = rk_integrator

vehicle.dyn_body.set_name("veh")
vehicle.dyn_body.integ_frame_name = "Space.inertial"
vehicle.dyn_body.translational_dynamics = True
vehicle.dyn_body.rotational_dynamics = True

# Initialize vehicle properties and state
exec(compile(open("Modified_data/vehicle_mass_props.py", "rb").read(),
             "Modified_data/vehicle_mass_props.py", 'exec'))

exec(compile(open("Modified_data/vehicle_state.py", "rb").read(),
             "Modified_data/vehicle_state.py", 'exec'))

# Connect Unity interface to JEOD state
unity_interface.position_source = \
    vehicle.dyn_body.composite_body.state.trans.position

unity_interface.velocity_source = \
    vehicle.dyn_body.composite_body.state.trans.velocity

dynamics.dyn_manager.add_body_action(vehicle.mass_init)
dynamics.dyn_manager.add_body_action(vehicle.trans_init)
dynamics.dyn_manager.add_body_action(vehicle.rot_init)

trick.sim_services.exec_set_terminate_time(10.0)