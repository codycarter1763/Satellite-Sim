def log_state(log_cycle):

    recording_group_name = "state"

    dr_group = trick.sim_services.DRAscii(recording_group_name)
    dr_group.thisown = 0

    dr_group.set_cycle(log_cycle)
    dr_group.freq = trick.DR_Always

    # Position
    for i in range(3):
        dr_group.add_variable(
            f"vehicle.dyn_body.composite_body.state.trans.position[{i}]"
        )

    # Velocity
    for i in range(3):
        dr_group.add_variable(
            f"vehicle.dyn_body.composite_body.state.trans.velocity[{i}]"
        )

    # Aerodynamic force
    for i in range(3):
        dr_group.add_variable(
            f"interactions.aero_drag.aero_force[{i}]"
        )

    # Atmosphere
    dr_group.add_variable("vehicle.atmos_state.density")
    dr_group.add_variable("vehicle.atmos_state.pressure")
    dr_group.add_variable("vehicle.atmos_state.temperature")

    # Quaternion
    dr_group.add_variable(
        "vehicle.lvlh_frame.frame.state.rot.Q_parent_this.scalar"
    )

    for i in range(3):
        dr_group.add_variable(
            f"vehicle.lvlh_frame.frame.state.rot.Q_parent_this.vector[{i}]"
        )

    trick.add_data_record_group(dr_group)

    return