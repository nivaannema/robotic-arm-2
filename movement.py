import math

ELBOW_ANGLE_OFFSET = 5.0

def dToR(degrees):
    return degrees * (math.pi / 180)
    # This function (dToR) is for converting degrees to radians

def rToD(radians):
    return radians * (180.0 / math.pi)
    # This function (rToD) is for converting radians to degrees

def calculate_fk(data):
    base_angle = int(data["base"])
    shoulder_angle = int(data["shoulder"])
    elbow_angle = int(data["elbow"]) - ELBOW_ANGLE_OFFSET
    wrist_tilt_angle = int(data["wristtilt"])

    theta_base = dToR(base_angle - 90)

    base_height = 96.0       
    spine_length = 194.0     
    offset_length = 50.0    
    forearm_length = 150.0   
    wrist_length = 130.0     

    theta_shoulder = dToR(shoulder_angle)

    ux = math.cos(theta_shoulder)
    uz = math.sin(theta_shoulder)

    x_spine = spine_length * ux
    z_spine = spine_length * uz

    dx = offset_length * uz
    dz = -offset_length * ux

    x_elbow = x_spine + dx
    z_elbow = z_spine + dz

    total_forearm_angle = theta_shoulder - dToR(elbow_angle)

    x_forearm_tip = x_elbow + (forearm_length * math.cos(total_forearm_angle))
    z_forearm_tip = z_elbow + (forearm_length * math.sin(total_forearm_angle))

    gamma_wrist = dToR(-1 * (wrist_tilt_angle - 90))
    total_wrist_angle = total_forearm_angle + gamma_wrist

    x_tip_2d = x_forearm_tip + (wrist_length * math.cos(total_wrist_angle))
    z_tip_2d = z_forearm_tip + (wrist_length * math.sin(total_wrist_angle))

    def project_3d(x_planar, z_planar):
        return {
            "x": round(x_planar * math.cos(theta_base)),
            "y": round(x_planar * math.sin(theta_base)),
            "z": round(z_planar + base_height)
        }

    # Joint 0: Base rotation axis on the ground
    p0 = {"x": 0, "y": 0, "z": 0}

    # Joint 1: Shoulder Rotation - At the height of the base pedestal
    p1 = {"x": 0, "y": 0, "z": round(base_height)}

    # Corner of the L shaped upper arm
    p_spine = project_3d(x_spine, z_spine)

    # Joint 2: Elbow Axis
    p2 = project_3d(x_elbow, z_elbow)

    # Joint 3: Wrist Tilt Axis
    p3 = project_3d(x_forearm_tip, z_forearm_tip)

    # Joint 4: Claw Tip
    p4 = project_3d(x_tip_2d, z_tip_2d)

    return {
        "x": p4["x"],
        "y": p4["y"],
        "z": p4["z"],
        "joints": [p0, p1, p_spine, p2, p3, p4]
    }

def plan_motion_sequence(current_angles, target_angles):
    """
    Sequences joint execution in strict order:
    1. Base
    2. Elbow
    3. Wrist Tilt
    4. Shoulder
    """

    step_1 = dict(current_angles)
    step_1["base"] = target_angles["base"]

    step_2 = dict(step_1)
    step_2["elbow"] = target_angles["elbow"]

    step_3 = dict(step_2)
    step_3["wristtilt"] = target_angles["wristtilt"]

    step_4 = dict(target_angles)

    steps = [step_1, step_2, step_3, step_4]

    for idx, step in enumerate(steps, 1):
        if check_collision_with_camera(step):
            raise ValueError(f"Motion step {idx} collides with camera zone!")

    return steps

CAMERA_BOX = {
    "x_min": 185.0, "x_max": 305.0,
    "y_min": -150.0, "y_max": -105.0,
    "z_min": 0.0, "z_max": 500.0
}

def check_collision_with_camera(angles_dict):
    """
    Runs forward kinematics on a set of angles and checks if any joint
    coordinates falls inside the camera exclusion box.
    Returns True if a collision is detected.
    """

    fk = calculate_fk(angles_dict)
    for joint in fk["joints"]:
        x, y, z = joint["x"], joint["y"], joint["z"]
        if (CAMERA_BOX["x_min"] <= x <= CAMERA_BOX["x_max"] and
            CAMERA_BOX["y_min"] <= y <= CAMERA_BOX["y_max"] and
            CAMERA_BOX["z_min"] <= z <= CAMERA_BOX["z_max"]):
            return True
    return False

def calculate_ik(target_x, target_y, target_z, pitch_deg=-90.0):
    """
    Solves inverse kinematics for the exact geometry defined in calculate_fk.
    target_x, target_y, target_z: mm coordinates
    pitch_deg: claw angle relative to horizontal plane (-90 = straight down, 0 = forward)
    """

    if target_x < 100.0:
        return {"reachable": False, "error": f"Target X ({target_x}) violates base pedestal clearance (min: 100mm)"}

    if target_y < -90.0:
        return {"reachable": False, "error": f"Target Y ({target_y}) violates camera mount boundary (min: -90mm)"}

    if target_z < 10.0:
        return {"reachable": False, "error": f"Target Z ({target_z}) violates table surface limit (min: 10mm)"}

    base_height = 96.0
    spine_len = 194.0
    offset_len = 50.0
    forearm_len = 150.0
    wrist_len = 130.0      

    theta_base = math.atan2(target_y, target_x)
    base_angle = round(rToD(theta_base) + 90.0)

    r_target = math.hypot(target_x, target_y)
    z_target_rel = target_z - base_height

    pitch_rad = dToR(pitch_deg)
    x_wrist = r_target - (wrist_len * math.cos(pitch_rad))
    z_wrist = z_target_rel - (wrist_len * math.sin(pitch_rad))

    best_alpha = None
    min_err = float("inf")

    for deg in range(180, -1, -1):
        a = dToR(deg)
        ux = math.cos(a)
        uz = math.sin(a)
        xe = spine_len * ux + offset_len * uz
        ze = spine_len * uz - offset_len * ux
        dist = math.hypot(x_wrist - xe, z_wrist - ze)
        err = abs(dist - forearm_len)

        t_forearm = math.atan2(z_wrist - ze, x_wrist - xe)
        e_deg = rToD(a - t_forearm)
        if  0.0 <= e_deg <= 180.0:
            if err < min_err:
                min_err = err
                best_alpha = a

    if min_err > 5.0:
        return {"reachable": False, "error": "Target out of reach"}

    original_best_alpha = best_alpha
    for fine_step in range(-20, 21):
        a = original_best_alpha + dToR(fine_step * 0.05)
        ux = math.cos(a)
        uz = math.sin(a)
        xe = spine_len * ux + offset_len * uz 
        ze = spine_len * uz - offset_len * ux
        dist = math.hypot(x_wrist - xe, z_wrist - ze)
        err = abs(dist - forearm_len)

        t_forearm = math.atan2(z_wrist - ze, x_wrist - xe)
        e_deg = rToD(a - t_forearm)
        if 0.0 <= e_deg <= 180.0:
            if err < min_err:
                min_err = err
                best_alpha = a

    shoulder_angle = round(rToD(best_alpha))

    ux = math.cos(best_alpha)
    uz = math.sin(best_alpha)
    x_elbow = spine_len * ux + offset_len * uz
    z_elbow = spine_len * uz - offset_len * ux

    total_forearm_angle = math.atan2(z_wrist - z_elbow, x_wrist - x_elbow)

    calibrated_elbow = rToD(best_alpha - total_forearm_angle)

    elbow_angle = round(calibrated_elbow + ELBOW_ANGLE_OFFSET)

    gamma_wrist = pitch_rad - total_forearm_angle
    wrist_tilt_angle = round(90.0 - rToD(gamma_wrist))

    solution = {
        "reachable": True,
        "base": int(max(0, min(180, base_angle))),
        "shoulder": int(max(0, min(180, shoulder_angle))),
        "elbow": int(max(0, min(180, elbow_angle))),
        "wristtilt": int(max(0, min(180, wrist_tilt_angle)))
    }

    if check_collision_with_camera(solution):
        return {"reachable": False, "error": "Arm trajcetory intersects camera bounding box"}

    return {
        "reachable": True,
        **solution
    }

if __name__ == "__main__":
    print("--- Running Multi-Pose Kinematics Round-Trip Test ---")

    test_poses = [
        {"name": "Neutral Forward", "base": 90, "shoulder": 130, "elbow": 140, "wristtilt": 90},
        {"name": "High Reach",       "base": 90, "shoulder": 150, "elbow": 160, "wristtilt": 90},
        {"name": "Rotated Side",     "base": 45, "shoulder": 120, "elbow": 130, "wristtilt": 75}
    ]

    for p in test_poses:
        fk = calculate_fk(p)
       
        theta_s = dToR(p["shoulder"])
        total_forearm = theta_s - dToR(p["elbow"])
        gamma = dToR(-1 * (p["wristtilt"] - 90))
        pitch = rToD(total_forearm + gamma)

        ik = calculate_ik(fk['x'], fk['y'], fk['z'], pitch_deg=pitch)

        if ik.get("reachable"):
            v_fk = calculate_fk(ik)
            dx = abs(fk['x'] - v_fk['x'])
            dy = abs(fk['y'] - v_fk['y'])
            dz = abs(fk['z'] - v_fk['z'])
            print(f"[{p['name']}] dX={dx}mm, dY={dy}mm, dZ={dz}mm | Solved: S={ik['shoulder']} E={ik['elbow']} W={ik['wristtilt']}")
        else:
            print(f"[{p['name']}] Failed: {ik.get('error')}")