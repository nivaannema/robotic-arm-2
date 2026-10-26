from flask_cors import CORS 
import serial_comms
from movement import calculate_ik, calculate_fk
from arm_config import (
    MOVEMENT_DURATION_MS,
    build_color_game_sequence,
    build_dice_sequence,
)
import logging
import threading
import time
from vision import CARD_COLORS, VisionService

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    Response,
    stream_with_context,
)

app = Flask(__name__)
CORS(app)
vision_service = VisionService()
game_state = {
    "status": "waiting_for_colour",
    "selected_colour": None,
    "selection_source": None,
    "current_stage": None,
    "message": "Show a colour card or choose a colour manually, then lock it.",
}
game_state_lock = threading.Lock()

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

@app.route("/")
def index():
    return render_template("index.html")


def update_game_state(**updates):
    with game_state_lock:
        game_state.update(updates)
        return dict(game_state)


def game_state_snapshot():
    with game_state_lock:
        return dict(game_state)


def set_current_game_stage(stage):
    update_game_state(
        current_stage=stage,
        message=f"Moving through stage: {stage.replace('_', ' ')}.",
    )


def run_game_phase(sequence, running_status, done_status, done_message, home_first=False):
    try:
        if home_first:
            update_game_state(
                status="homing",
                current_stage="home",
                message=(
                    "Homing. Confirmed starting pose was HOME; "
                    "moving to home, then waiting 6 seconds."
                ),
            )
            serial_comms.home_arm(
                start_pose=serial_comms.STARTUP_POSE,
                post_home_delay_seconds=6,
            )

        update_game_state(
            status=running_status,
            current_stage=None,
            message="Starting ordered arm movements.",
        )
        serial_comms.execute_pose_sequence(
            sequence,
            stage_callback=set_current_game_stage,
        )
        update_game_state(
            status=done_status,
            current_stage=None,
            message=done_message,
        )
    except Exception as error:
        app.logger.exception("Game movement phase failed")
        failed_stage = game_state_snapshot()["current_stage"]
        update_game_state(
            status="error",
            message=(
                f"Movement stopped during {failed_stage or 'an unknown stage'}: {error}. "
                "Check the arm's actual position before another run."
            ),
        )


def start_game_phase(sequence, running_status, done_status, done_message, home_first=False):
    worker = threading.Thread(
        target=run_game_phase,
        args=(sequence, running_status, done_status, done_message, home_first),
        name=f"robot-game-{running_status}",
        daemon=True,
    )
    worker.start()

@app.route("/control", methods=["POST"])
def control():
    if game_state_snapshot()["status"] in {
        "homing",
        "running_block",
        "running_dice",
        "running_dice_only",
    }:
        return jsonify({
            "error": "Manual slider commands are disabled while the game sequence is moving."
        }), 423

    data = request.json
    serial_comms.send_command(
        data,
        duration_ms=data.get("duration_ms", MOVEMENT_DURATION_MS),
    )
    coords = calculate_fk(data)
    return jsonify({
        "status": "OK",
        "x": coords["x"],
        "y": coords["y"],
        "z": coords["z"],
        "joints": coords.get("joints", [])
    })

@app.route("/solve_ik", methods=['POST'])
def solve_ik_endpoint():
    data = request.get_json() or {}
    try:
        x = float(data.get('x', 0))
        y = float(data.get('y', 0))
        z = float(data.get('z', 0))
        pitch = float(data.get('pitch', -90))

        result = calculate_ik(x, y, z, pitch_deg=pitch)
        return jsonify(result)
    except Exception as e:
        return jsonify({"reachable": False, "error": str(e)}), 400

def vision_frames():
    while True:
        jpeg = vision_service.read_jpeg()

        if jpeg is None:
            time.sleep(0.05)
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b"\r\n"
        )

@app.route('/vision_feed')
def vision_feed():
    try:
        vision_service.start()
    except RuntimeError as e:
        return str("error"), 503

    return Response(
        stream_with_context(vision_frames()),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )

@app.route("/vision_mode", methods=["POST"])
def vision_mode():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("enabled"), bool):
        return jsonify({"error": "Expected JSON with boolean 'enabled'"}), 400

    vision_service.set_calibration_mode(data["enabled"])
    return jsonify({"status": "OK", "enabled": data["enabled"]})

@app.route("/vision_calibrate", methods=["POST"])
def vision_calibrate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    color = data.get("color")
    coordinates = [
        data.get("x"),
        data.get("y"),
        data.get("width"),
        data.get("height"),
    ]

    if not isinstance(color, str):
        return jsonify({"error": "A colour name is required"}), 400

    try:
        x, y, width, height = map(float, coordinates)
    except (TypeError, ValueError):
        return jsonify({"error": "Selection coordinates must be numbers"}), 400

    if (
        not all(0 <= value <= 1 for value in (x, y, width, height))
        or width <= 0
        or height <= 0
        or x + width > 1
        or y + height > 1
    ):
        return jsonify({"error": "Selection is outside the camera image"}), 400

    try:
        ranges = vision_service.calibrate_color(
            color.casefold(),
            x,
            y,
            width,
            height,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503

    return jsonify({
        "status": "OK",
        "color": color.casefold(),
        "ranges": ranges,
    })

@app.route("/game_start", methods=["POST"])
def game_start():
    state = game_state_snapshot()
    if state["status"] != "waiting_for_colour":
        if state["status"] in {
            "homing",
            "running_block",
            "awaiting_block_removal",
            "running_dice",
            "round_complete",
        }:
            return jsonify(state), 409
        return jsonify({
            **state,
            "error": "Reset the round before starting another run.",
        }), 409

    detected_colour = vision_service.get_selected_color()
    with game_state_lock:
        if game_state["status"] != "waiting_for_colour":
            return jsonify({
                **game_state,
                "error": "A game round has already started; reset before starting another.",
            }), 409
        selected_colour = game_state["selected_colour"] or detected_colour
        if selected_colour is None:
            return jsonify({
                "error": "No colour is selected. Choose a colour manually or wait for camera detection."
            }), 409

        try:
            sequence = build_color_game_sequence(selected_colour)
        except ValueError as error:
            return jsonify({"error": str(error)}), 409

        dice_index = next(
            (index for index, step in enumerate(sequence)
             if step["stage"] == "dice_approach"),
            None,
        )
        if dice_index is None:
            return jsonify({"error": "The configured sequence has no dice stage."}), 500
        block_sequence = sequence[:dice_index]
        game_state.update({
            "status": "homing",
            "selected_colour": selected_colour,
            "selection_source": (
                game_state["selection_source"] or "camera"
            ),
            "current_stage": "home",
            "message": (
                f"{selected_colour.title()} locked. Starting homing and the block "
                "pickup/delivery sequence."
            ),
        })
    start_game_phase(
        block_sequence,
        "running_block",
        "awaiting_block_removal",
        (
            "Block delivered. Remove it from the drop-off zone, make sure the "
            "die is in place, then click Continue."
        ),
        home_first=True,
    )
    return jsonify(game_state_snapshot()), 202


@app.route("/game_select_colour", methods=["POST"])
def game_select_colour():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("colour"), str):
        return jsonify({"error": "Choose a supported colour."}), 400

    selected_colour = data["colour"].casefold()
    if selected_colour not in CARD_COLORS:
        return jsonify({"error": "Choose one of the six supported colours."}), 400

    with game_state_lock:
        if game_state["status"] != "waiting_for_colour":
            return jsonify({
                "error": "Colours can only be selected before the round starts."
            }), 409
        game_state.update({
            "selected_colour": selected_colour,
            "selection_source": "manual",
            "message": f"{selected_colour.title()} selected manually.",
        })
        return jsonify(dict(game_state))


@app.route("/game_status", methods=["GET"])
def get_game_status():
    return jsonify(game_state_snapshot())

@app.route("/game_continue", methods=["POST"])
def game_continue():
    with game_state_lock:
        if game_state["status"] != "awaiting_block_removal":
            return jsonify({
                "error": "Lock a colour first; Continue is only available during the block-removal stage."
            }), 409

        selected_colour = game_state["selected_colour"]

    try:
        sequence = build_color_game_sequence(selected_colour)
    except ValueError as error:
        return jsonify({"error": str(error)}), 409

    dice_index = next(
        (index for index, step in enumerate(sequence)
         if step["stage"] == "dice_approach"),
        None,
    )
    if dice_index is None:
        return jsonify({"error": "The configured sequence has no dice stage."}), 500
    dice_sequence = sequence[dice_index:]

    with game_state_lock:
        if game_state["status"] != "awaiting_block_removal":
            return jsonify({
                "error": "The game phase has already changed; refresh the page and try again."
            }), 409
        game_state.update({
            "status": "running_dice",
            "current_stage": None,
            "message": "Block removal confirmed. Starting the dice sequence.",
        })

    start_game_phase(
        dice_sequence,
        "running_dice",
        "round_complete",
        "Dice sequence finished. The round is complete.",
    )
    return jsonify(game_state_snapshot()), 202


@app.route("/game_dice_roll", methods=["POST"])
def game_dice_roll():
    with game_state_lock:
        allowed_statuses = {
            "waiting_for_colour",
            "awaiting_block_removal",
            "round_complete",
            "dice_only_complete",
            "error",
        }
        if game_state["status"] not in allowed_statuses:
            return jsonify({
                "error": "The full dice sequence can only start when no other arm sequence is running."
            }), 409

    try:
        sequence = build_dice_sequence()
    except ValueError as error:
        return jsonify({"error": str(error)}), 409

    with game_state_lock:
        if game_state["status"] not in allowed_statuses:
            return jsonify({
                "error": "Another arm sequence started; refresh the page before trying again."
            }), 409
        game_state.update({
            "status": "running_dice_only",
            "current_stage": None,
            "message": "Starting the full dice pickup and roll sequence.",
        })

    start_game_phase(
        sequence,
        "running_dice_only",
        "dice_only_complete",
        "Full dice pickup and roll sequence completed.",
    )
    return jsonify(game_state_snapshot()), 202


@app.route("/game_reset", methods=["POST"])
def game_reset():
    with game_state_lock:
        if game_state["status"] in {
            "homing",
            "running_block",
            "running_dice",
            "running_dice_only",
        }:
            return jsonify({
                "error": "Cannot reset while the arm is moving. Wait for the phase to finish."
            }), 409

        game_state.update({
            "status": "waiting_for_colour",
            "selected_colour": None,
            "selection_source": None,
            "current_stage": None,
            "message": "Show a colour card or choose a colour manually, then lock it.",
        })
        return jsonify(dict(game_state))

if __name__ == "__main__":
    print("Server running...")
    app.run(port=5001, debug=True, use_reloader=False)