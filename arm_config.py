CLAW_OPEN = 65
CLAW_GRIP_DICE = 34
CLAW_GRIP_BLOCK = 46
ELBOW_CALIBRATION_OFFSET = 2

# All poses and transitions have been manually tested; game execution is enabled.
MOVEMENT_ENABLED = True
MOVEMENT_DURATION_MS = 3000
BASE_MOVEMENT_DURATION_MS = 1000

DEFAULT_MOVEMENT_ORDER = (
    "base",
    "elbow",
    "wristtilt",
    "shoulder",
    "wristyaw",
    "claw",
)

MOVEMENT_ORDER_OVERRIDES = {
    # "blue_pickup": ("base", "shoulder", "elbow", "wristtilt", "wristyaw", "claw"),
    "home_after_block_delivery": (
        "shoulder",
        "elbow",
        "base",
        "wristtilt",
        "wristyaw",
        "claw",
    ),
}

BLOCK_POSES = {
    "blue": {
        "approach": {"base": 90, "shoulder": 76, "elbow": 95, "wristtilt": 116, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 90, "shoulder": 53.5, "elbow": 95, "wristtilt": 116, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 90, "shoulder": 53.5, "elbow": 95, "wristtilt": 116, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 90, "shoulder": 76, "elbow": 95, "wristtilt": 116, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
    "yellow": {
        "approach": {"base": 103, "shoulder": 90, "elbow": 91, "wristtilt": 92, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 103, "shoulder": 47, "elbow": 91, "wristtilt": 92, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 103, "shoulder": 47, "elbow": 91, "wristtilt": 92, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 103, "shoulder": 90, "elbow": 91, "wristtilt": 92, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
    "orange": {
        "approach": {"base": 90, "shoulder": 80, "elbow": 93, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 90, "shoulder": 47, "elbow": 93, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 90, "shoulder": 47, "elbow": 93, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 90, "shoulder": 80, "elbow": 93, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
    "green": {
        "approach": {"base": 102, "shoulder": 80, "elbow": 93, "wristtilt": 115, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 102, "shoulder": 51.5, "elbow": 93, "wristtilt": 115, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 102, "shoulder": 51.5, "elbow": 93, "wristtilt": 115, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 102, "shoulder": 80, "elbow": 93, "wristtilt": 115, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
    "red": {
        "approach": {"base": 79, "shoulder": 80, "elbow": 91, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 79, "shoulder": 47, "elbow": 91, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 79, "shoulder": 47, "elbow": 91, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 79, "shoulder": 80, "elbow": 91, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
    "white": {
        "approach": {"base": 79, "shoulder": 90, "elbow": 113, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "prepickup": {"base": 79, "shoulder": 55, "elbow": 113, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_OPEN},
        "pickup": {"base": 79, "shoulder": 55, "elbow": 113, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
        "retreat": {"base": 79, "shoulder": 90, "elbow": 113, "wristtilt": 90, "wristyaw": 90, "claw": CLAW_GRIP_BLOCK},
    },
}

DICE_POSES = {
    "approachDie": {
        "base": 91,
        "shoulder": 100,
        "elbow": 136,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
    "prepickup": {
        "base": 91,
        "shoulder": 73,
        "elbow": 136,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
    "pickup": {
        "base": 91,
        "shoulder": 73,
        "elbow": 136,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_GRIP_DICE,
    },
    "approachDrop": {
        "base": 91,
        "shoulder": 100,
        "elbow": 139,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_GRIP_DICE,
    },
    "roll": {
        "base": 80,
        "shoulder": 100,
        "elbow": 155,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
    "retreat": {
        "base": 90,
        "shoulder": 180,
        "elbow": 175,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
}

HOME_POSE = {
    "base": 90,
    "shoulder": 180,
    "elbow": 175,
    "wristtilt": 90,
    "wristyaw": 90,
    "claw": CLAW_OPEN,
}

BLOCK_DELIVERY_POSES = {
    "approach": {
        "base": 117,
        "shoulder": 90,
        "elbow": 149,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_GRIP_BLOCK,
    },
    "predrop": {
        "base": 117,
        "shoulder": 78,
        "elbow": 149,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_GRIP_BLOCK,
    },
    "drop": {
        "base": 117,
        "shoulder": 78,
        "elbow": 149,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
    "retreat": {
        "base": 117,
        "shoulder": 78,
        "elbow": 90,
        "wristtilt": 90,
        "wristyaw": 90,
        "claw": CLAW_OPEN,
    },
    "home": HOME_POSE,
}

SERVO_KEYS = (
    "base",
    "shoulder",
    "elbow",
    "wristtilt",
    "wristyaw",
    "claw",
)


def calibrate_pose(pose):
    """Return a pose copy with the elbow calibration offset applied."""
    elbow = pose.get("elbow")
    if (
        isinstance(elbow, bool)
        or not isinstance(elbow, (int, float))
        or not 0 <= elbow <= 180
    ):
        raise ValueError(f"Pose has an invalid elbow angle: {elbow!r}")

    calibrated_pose = dict(pose)
    calibrated_pose["elbow"] = elbow + ELBOW_CALIBRATION_OFFSET
    if calibrated_pose["elbow"] > 180:
        raise ValueError(
            f"Calibrated elbow angle exceeds 180 degrees: "
            f"{calibrated_pose['elbow']!r}"
        )
    return calibrated_pose


def _pose_with_claw(pose, claw_angle, pose_name):
    """Return a validated copy of a taught pose with the requested claw angle."""
    if not isinstance(pose, dict):
        raise ValueError(f"{pose_name} has not been recorded yet.")

    missing = [key for key in SERVO_KEYS if key not in pose]
    if missing:
        raise ValueError(
            f"{pose_name} is missing servo angles:{', '.join(missing)}"
            )
    
    command = {key: pose[key] for key in SERVO_KEYS}
    for key, angle in command.items():
        if (
            isinstance(angle, bool)
            or not isinstance(angle, (int, float))
            or not 0 <= angle <= 180
        ):
            raise ValueError(
                f"Pose '{pose_name}' has an invalid angle for '{key}': {angle!r}"
            )

    command["claw"] = claw_angle
    try:
        return calibrate_pose(command)
    except ValueError as error:
        raise ValueError(f"Pose '{pose_name}': {error}") from error


def _build_pose_step(stage, pose):
    movement_order = MOVEMENT_ORDER_OVERRIDES.get(
        stage,
        DEFAULT_MOVEMENT_ORDER,
    )
    if (
        not isinstance(movement_order, (tuple, list))
        or len(movement_order) != len(SERVO_KEYS)
        or set(movement_order) != set(SERVO_KEYS)
    ):
        raise ValueError(f"Invalid movement order configured for stage '{stage}'.")

    return {
        "stage": stage,
        "angles": _pose_with_claw(
            pose,
            pose["claw"] if isinstance(pose, dict) else None,
            stage,
        ),
        "movement_order": tuple(movement_order),
        "duration_ms": MOVEMENT_DURATION_MS,
    }


def build_dice_sequence():
    """Build the complete dice pickup, roll, and retreat sequence."""
    stages = (
        ("dice_approach", "approachDie"),
        ("dice_prepickup", "prepickup"),
        ("dice_pickup", "pickup"),
        ("dice_approach_drop", "approachDrop"),
        ("dice_roll", "roll"),
        ("dice_retreat", "retreat"),
    )
    return [
        _build_pose_step(stage, DICE_POSES[pose_name])
        for stage, pose_name in stages
    ]


def build_color_game_sequence(chosen_color):
    """
    Build, but do not execute, the servo commands for one game round.

    The returned list contains {"stage": ..., "angles": ...} entries in
    execution order. Each pose is copied and validated; no hardware commands
    are sent by this function.
    """
    if not isinstance(chosen_color, str):
        raise ValueError("Chosen colour must be a string.")

    color = chosen_color.casefold()
    if color not in BLOCK_POSES:
        raise ValueError(f"Unknown block colour: {chosen_color}")

    sequence = []

    def add_pose(stage, pose):
        sequence.append(_build_pose_step(stage, pose))

    block_poses = BLOCK_POSES[color]
    add_pose(f"{color}_approach", block_poses["approach"])
    add_pose(f"{color}_prepickup", block_poses["prepickup"])
    add_pose(f"{color}_pickup", block_poses["pickup"])
    add_pose(f"{color}_retreat", block_poses["retreat"])

    add_pose("block_delivery_approach", BLOCK_DELIVERY_POSES["approach"])
    add_pose("block_delivery_predrop", BLOCK_DELIVERY_POSES["predrop"])
    add_pose("block_delivery_drop", BLOCK_DELIVERY_POSES["drop"])
    add_pose("block_delivery_retreat", BLOCK_DELIVERY_POSES["retreat"])

    blue_retreat_waypoint = dict(BLOCK_POSES["blue"]["retreat"])
    blue_retreat_waypoint["claw"] = CLAW_OPEN
    add_pose("blue_retreat_waypoint", blue_retreat_waypoint)
    add_pose("home_after_block_delivery", HOME_POSE)

    add_pose("dice_approach", DICE_POSES["approachDie"])
    add_pose("dice_prepickup", DICE_POSES["prepickup"])
    add_pose("dice_pickup", DICE_POSES["pickup"])
    add_pose("dice_approach_drop", DICE_POSES["approachDrop"])
    add_pose("dice_roll", DICE_POSES["roll"])
    add_pose("dice_retreat", DICE_POSES["retreat"])

    return sequence