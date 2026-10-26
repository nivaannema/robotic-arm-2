import threading

import cv2
import numpy as np

CARD_COLORS = {"blue", "yellow", "orange", "green", "red", "white"}
STABLE_COLOR_FRAMES = 8
CARD_MIN_AREA_RATIO = 0.05

class VisionService:
    def __init__(self):
        self.camera = None
        self.lock = threading.RLock()
        self.latest_frame = None
        self.calibration_mode = False

        self.color_ranges = {
            "blue": ([100, 100, 50], [130, 255, 255]),
            "yellow": ([20, 100, 100], [40, 255, 255]),
            "orange": ([5, 100, 100], [20, 255, 255]),
            "green": ([35, 60, 50], [90, 255, 255]),
            "red": ([0, 100, 100], [10, 255, 255]),
            "white": ([0, 0, 180], [180, 60, 255]),
        }

        self.qr_detector = cv2.QRCodeDetector()
        self.selected_color = None
        self.pending_color = None
        self.stable_color_frames = 0
        self.previous_payload = None

    def start(self):
        with self.lock:
            if self.camera is not None and self.camera.isOpened():
                return

            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            if not self.camera.isOpened():
                self.camera.release()
                self.camera = None
                raise RuntimeError("Could not open camera 0")

    def set_calibration_mode(self, enabled):
        with self.lock:
            self.calibration_mode = enabled

    def get_selected_color(self):
        with self.lock:
            return self.selected_color

    def calibrate_color(self, color_name, x, y, width, height):
        if color_name not in CARD_COLORS:
            raise ValueError("Unsupported colour")

        with self.lock:
            if self.latest_frame is None:
                raise RuntimeError("The camera has not produced a frame yet")

            frame_height, frame_width = self.latest_frame.shape[:2]
            left = round(x * frame_width)
            top = round(y * frame_height)
            right = round((x + width) * frame_width)
            bottom = round((y + height) * frame_height)

            left = max(0, min(left, frame_width - 1))
            top = max(0, min(top, frame_height - 1))
            right = max(left + 1, min(right, frame_width))
            bottom = max(top + 1, min(bottom, frame_height))

            roi = cv2.cvtColor(
                self.latest_frame[top:bottom, left:right],
                cv2.COLOR_BGR2HSV,
            )

            h_values = roi[:, :, 0].reshape(-1)
            s_values = roi[:, :, 1].reshape(-1)
            v_values = roi[:, :, 2].reshape(-1)

            sample_mask = v_values > 40
            if color_name != "white":
                sample_mask &= s_values > 35

            if not np.any(sample_mask):
                raise ValueError(
                    "The selected area has no usable pixels for calibration"
                )

            h_values = h_values[sample_mask]
            s_values = s_values[sample_mask]
            v_values = v_values[sample_mask]

            h_min = max(0, int(np.percentile(h_values, 5)) - 15)
            h_max = min(180, int(np.percentile(h_values, 95)) + 15)
            s_min = max(0, int(np.percentile(s_values, 5)) - 20)
            s_max = min(255, int(np.percentile(s_values, 95)) + 20)
            v_min = max(0, int(np.percentile(v_values, 5)) - 20)

            if color_name == "white":
                self.color_ranges[color_name] = (
                    [0, 0, max(0, v_min - 20)],
                    [180, 80, 255],
                )
            else:
                v_max = min(255, int(np.percentile(v_values, 95)) + 20)
                self.color_ranges[color_name] = (
                    [h_min, s_min, v_min],
                    [h_max, s_max, v_max],
                )

            return self.color_ranges[color_name]

    def _detect_colors(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detections = []
        min_area = max(
            1500,
            int(frame.shape[0] * frame.shape[1] * CARD_MIN_AREA_RATIO),
        )
        cleanup_kernel = np.ones((5, 5), np.uint8)

        for color_name, (lower, upper) in self.color_ranges.items():
            mask = cv2.inRange(
                hsv,
                np.array(lower, dtype=np.uint8),
                np.array(upper, dtype=np.uint8),
            )
            mask = cv2.morphologyEx(
                mask,
                cv2.MORPH_OPEN,
                cleanup_kernel,
            )
            mask = cv2.morphologyEx(
                mask,
                cv2.MORPH_CLOSE,
                cleanup_kernel,
            )

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue

                x, y, width, height = cv2.boundingRect(contour)
                aspect_ratio = width / height

                if (
                    width * height > frame.shape[0] * frame.shape[1] * 0.8
                    or not 0.3 <= aspect_ratio <= 3.5
                ):
                    continue

                detections.append(
                    (color_name, x, y, width, height, area)
                )

        return detections

    def _scan_qr(self, frame):
        try:
            payload, points, _ = self.qr_detector.detectAndDecode(frame)
        except cv2.error as error:
            print(f"QR scan skipped for this frame: {error}")
            return None, None

        if not payload:
            return None, points

        color_name = payload.strip().casefold()
        if color_name not in CARD_COLORS:
            if payload != self.previous_payload:
                print(f"QR code '{payload}' is not a supported colour.")
            return None, points

        return color_name, points

    def read_jpeg(self):
        with self.lock:
            self.start()
            success, frame = self.camera.read()

            if not success:
                return None

            self.latest_frame = frame.copy()
            scanned_color, qr_points = self._scan_qr(frame)

            if qr_points is not None:
                polygon = np.asarray(qr_points, dtype=np.int32).reshape(-1, 1, 2)
                cv2.polylines(frame, [polygon], True, (255, 0, 255), 3)

            detections = self._detect_colors(frame)
            detected_color = (
                max(detections, key=lambda detection: detection[5])[0]
                if detections
                else None
            )

            if detected_color:
                white_qr_required = (
                    detected_color == "white" and scanned_color != "white"
                )

                if white_qr_required:
                    self.pending_color = None
                    self.stable_color_frames = 0
                    if scanned_color:
                        qr_status = (
                            f"White card requires white QR; read {scanned_color}"
                        )
                    else:
                        qr_status = "White card requires readable white QR"
                else:
                    if detected_color == self.pending_color:
                        self.stable_color_frames += 1
                    else:
                        self.pending_color = detected_color
                        self.stable_color_frames = 1

                    if (
                        self.stable_color_frames >= STABLE_COLOR_FRAMES
                        and self.selected_color != detected_color
                    ):
                        self.selected_color = detected_color
                        print(f"Student colour selected: {detected_color}")

                    if detected_color == "white":
                        qr_status = "White QR confirmed"
                    elif scanned_color == detected_color:
                        qr_status = "QR agrees; colour is sufficient"
                    elif scanned_color:
                        qr_status = (
                            f"QR says {scanned_color}; ignored for colour selection"
                        )
                    else:
                        qr_status = "Colour detection; QR not required"
            else:
                self.pending_color = None
                self.stable_color_frames = 0

                qr_status = (
                    "QR detected; show the coloured card"
                    if scanned_color
                    else "No card colour detected"
                )

            self.previous_payload = scanned_color

            if self.calibration_mode:
                for color_name, x, y, width, height, _ in detections:
                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + width, y + height),
                        (0, 255, 0),
                        2,
                    )
                    cv2.putText(
                        frame,
                        color_name,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
                mode_text = "CALIBRATION MODE"
            else:
                mode_text = "NORMAL MODE"

            card_text = (
                f"Card: {detected_color or 'none'} | {qr_status} | "
                f"Selected: {self.selected_color or 'none'}"
            )

            cv2.putText(
                frame,
                mode_text,
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                card_text,
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 0, 255),
                2,
            )

            encoded, jpeg = cv2.imencode(".jpg", frame)
            if not encoded:
                raise RuntimeError("Could not encode camera frame as JPEG")

            return jpeg.tobytes()