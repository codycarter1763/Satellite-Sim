def set_state(vehicle, position, velocity, eigen_angle, eigen_axis, ang_velocity):

    vehicle.trans_init.set_subject_body(vehicle.dyn_body)
    vehicle.trans_init.reference_ref_frame_name = "Space.inertial"
    vehicle.trans_init.body_frame_id = "composite_body"

    vehicle.trans_init.position = position
    vehicle.trans_init.velocity = velocity

    vehicle.rot_init.set_subject_body(vehicle.dyn_body)
    vehicle.rot_init.reference_ref_frame_name = "Space.inertial"
    vehicle.rot_init.body_frame_id = "composite_body"

    vehicle.rot_init.orientation.data_source = \
        trick.Orientation.InputEigenRotation

    vehicle.rot_init.orientation.eigen_angle = \
        trick.sim_services.attach_units("degree", eigen_angle)

    vehicle.rot_init.orientation.eigen_axis = eigen_axis

    vehicle.rot_init.ang_velocity = \
        trick.sim_services.attach_units("degree/s", ang_velocity)