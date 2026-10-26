import itertools
import json
import threading
import time

import serial
from arm_config import (
    BASE_MOVEMENT_DURATION_MS,
    HOME_POSE,
    MOVEMENT_DURATION_MS,
    MOVEMENT_ENABLED,
    calibrate_pose,
)


SERIAL_PORT = "/dev/cu.usbmodem1101"
JOINT_SETTLE_DELAY_SECONDS = 0.12
POSE_SETTLE_DELAY_SECONDS = 0.4
PICKUP_SETTLE_DELAY_SECONDS = 0.8
STARTUP_POSE = {
    **calibrate_pose(HOME_POSE),
}
arduino = None

SERVO_KEYS = (
    "base",
    "shoulder",
    "elbow",
    "wristtilt",
    "wristyaw",
    "claw",
)

_command_ids = itertools.count(1)
_serial_lock = threading.RLock()


def _get_arduino():
    global arduino

    if arduino is None:
        arduino = serial.Serial(SERIAL_PORT, 115200, timeout=0.1)
        time.sleep(2)
        arduino.reset_input_buffer()

    return arduino


def _wait_for_reply(command_id, expected_prefix, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        reply = _get_arduino().readline().decode("utf-8", errors="replace").strip()

        if reply == f"{expected_prefix}:{command_id}":
            return
        if reply == f"ERROR:{command_id}" or reply == "ERROR:-1":
            raise RuntimeError(f"Arduino rejected command {command_id}")

    raise TimeoutError(
        f"Arduino did not reply {expected_prefix}:{command_id}"
    )


def send_command(data, duration_ms=MOVEMENT_DURATION_MS, wait_until_done=False):
    """Send one target pose; optionally wait for its Arduino completion reply."""
    with _serial_lock:
        command_id = next(_command_ids)

        payload = {}
        for key in SERVO_KEYS:
            angle = int(data[key])
            if not 0 <= angle <= 180:
                raise ValueError(f"{key} angle must be between 0 and 180")
            payload[key] = angle

        payload["cmd_id"] = command_id
        payload["duration_ms"] = max(300, min(int(duration_ms), 30000))
        payload["base_duration_ms"] = BASE_MOVEMENT_DURATION_MS

        message = json.dumps(payload) + "\n"
        device = _get_arduino()
        device.write(message.encode("utf-8"))
        device.flush()
        print("Sending JSON:", message.strip())

        if not wait_until_done:
            return command_id

        _wait_for_reply(
            command_id,
            "DONE",
            max(
                payload["duration_ms"],
                payload["base_duration_ms"],
            ) / 1000 + 5,
        )
        return command_id


def send_joint_command(joint, angle, duration_ms=MOVEMENT_DURATION_MS):
    """Move one joint and wait until the Arduino confirms it has arrived."""
    if joint not in SERVO_KEYS:
        raise ValueError(f"Unknown servo joint: {joint}")

    angle = int(angle)
    if not 0 <= angle <= 180:
        raise ValueError(f"{joint} angle must be between 0 and 180")

    with _serial_lock:
        command_id = next(_command_ids)
        duration_ms = max(300, min(int(duration_ms), 30000))
        if joint == "base":
            duration_ms = BASE_MOVEMENT_DURATION_MS
        payload = {
            joint: angle,
            "cmd_id": command_id,
            "duration_ms": duration_ms,
        }
        message = json.dumps(payload) + "\n"
        device = _get_arduino()
        device.write(message.encode("utf-8"))
        device.flush()
        print("Sending ordered joint JSON:", message.strip())

        _wait_for_reply(
            command_id,
            "DONE",
            duration_ms / 1000 + 5,
        )
        return command_id


def home_arm(
    start_pose=None,
    post_home_delay_seconds=6,
    duration_ms=MOVEMENT_DURATION_MS,
):
    """Sync from a known pose, move in order to HOME, then wait before returning."""
    start_pose = STARTUP_POSE if start_pose is None else start_pose
    if set(start_pose) != set(SERVO_KEYS):
        raise ValueError("The startup pose must provide all six servo angles.")

    for joint in SERVO_KEYS:
        angle = start_pose[joint]
        if isinstance(angle, bool) or not isinstance(angle, int) or not 0 <= angle <= 180:
            raise ValueError(f"Invalid startup angle for {joint}: {angle!r}")
        if joint in {"wristtilt", "wristyaw"} and not 10 <= angle <= 170:
            raise ValueError(f"{joint} startup angle must be between 10 and 170")

    if (
        isinstance(post_home_delay_seconds, bool)
        or not isinstance(post_home_delay_seconds, int)
        or post_home_delay_seconds < 0
    ):
        raise ValueError(
            "Post-home delay must be a non-negative whole number of seconds."
        )

    duration_ms = max(300, min(int(duration_ms), 30000))

    print(
        "Ensure the servo power is on and the arm is at the configured "
        "startup pose before homing."
    )
    with _serial_lock:
        command_id = next(_command_ids)
        payload = {
            "sync": 1,
            **{joint: int(start_pose[joint]) for joint in SERVO_KEYS},
            "cmd_id": command_id,
        }
        message = json.dumps(payload) + "\n"
        device = _get_arduino()
        device.write(message.encode("utf-8"))
        device.flush()
        print("Synchronizing startup pose:", message.strip())
        _wait_for_reply(command_id, "READY", 5)

        completed_commands = []
        home_joints = (
            "base",
            "elbow",
            "wristtilt",
            "shoulder",
            "wristyaw",
            "claw",
        )
        for joint in home_joints:
            completed_commands.append(
                send_joint_command(joint, STARTUP_POSE[joint], duration_ms)
            )
            time.sleep(JOINT_SETTLE_DELAY_SECONDS)

    print("Home pose reached.")
    time.sleep(POSE_SETTLE_DELAY_SECONDS)
    if post_home_delay_seconds:
        print(f"Waiting {post_home_delay_seconds} seconds at home.")
        time.sleep(post_home_delay_seconds)

    return completed_commands


def execute_pose_sequence(sequence, stage_callback=None):
    """Execute ordered pose steps, waiting for each individual joint to finish."""
    if not MOVEMENT_ENABLED:
        raise RuntimeError(
            "Automated movement is disabled in arm_config.py; poses must be "
            "physically validated before enabling it."
        )

    completed_commands = []
    with _serial_lock:
        for step in sequence:
            if stage_callback is not None:
                stage_callback(step["stage"])

            angles = step["angles"]
            movement_order = step["movement_order"]
            duration_ms = step.get("duration_ms", 3000)

            if set(angles) != set(SERVO_KEYS):
                raise ValueError(
                    f"Stage {step.get('stage', '<unknown>')} has invalid angles"
                )
            if (
                len(movement_order) != len(SERVO_KEYS)
                or set(movement_order) != set(SERVO_KEYS)
            ):
                raise ValueError(
                    f"Stage {step.get('stage', '<unknown>')} has invalid movement order"
                )

            for joint in movement_order:
                completed_commands.append(
                    send_joint_command(joint, angles[joint], duration_ms)
                )
                time.sleep(JOINT_SETTLE_DELAY_SECONDS)

            pose_delay = (
                PICKUP_SETTLE_DELAY_SECONDS
                if step["stage"].endswith("_pickup")
                else POSE_SETTLE_DELAY_SECONDS
            )
            time.sleep(pose_delay)

    return completed_commands