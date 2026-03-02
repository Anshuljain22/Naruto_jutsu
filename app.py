import cv2
import numpy as np
import threading
from flask import Flask, Response, jsonify, send_from_directory, request
from flask_cors import CORS

from pose_detection.detector import PoseDetector
from gesture_engine.recognizer import GestureRecognizer
from effects.manager import EffectManager

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Per-session processing state
# Each visitor gets their own gesture + effect state via a session_id they
# generate client-side. State is lazily created on first frame received.
# ---------------------------------------------------------------------------
sessions = {}
sessions_lock = threading.Lock()

def get_session(session_id):
    """Return (or lazily create) the processing state for a session."""
    with sessions_lock:
        if session_id not in sessions:
            print(f"[session] Creating new session: {session_id}")
            sessions[session_id] = {
                "detector": PoseDetector(detection_con=0.6, track_con=0.6),
                "recognizer": GestureRecognizer(),
                "effect_manager": EffectManager(),
                "current_jutsu": "",
                "status_text": "Ready",
            }
        return sessions[session_id]

# ---------------------------------------------------------------------------
# Routes — static files
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# ---------------------------------------------------------------------------
# Core route: receive a raw webcam frame, return processed frame
# ---------------------------------------------------------------------------
@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    session_id = request.headers.get('X-Session-ID', 'default')
    state = get_session(session_id)

    # Decode incoming JPEG → numpy BGR array
    file_bytes = np.frombuffer(request.data, dtype=np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return Response(status=400)

    detector = state["detector"]
    recognizer = state["recognizer"]
    effect_manager = state["effect_manager"]

    # Run pose + hand detection
    detector.find_landmarks(frame, draw=False)
    pose_lms = detector.get_pose_landmarks(frame.shape)
    hands_lms = detector.get_hand_landmarks(frame.shape)
    mask = detector.get_segmentation_mask()

    # Gesture detection and effect triggering
    jutsu_triggered = recognizer.detect(pose_lms, hands_lms, frame.shape)
    if jutsu_triggered:
        effect_manager.trigger(jutsu_triggered, frame, pose_lms, mask)

    effect_manager.update()
    result = effect_manager.render(frame.copy())

    # Update session status
    if effect_manager.active_effect:
        jutsu_name = [k for k, v in effect_manager.effects.items()
                      if v == effect_manager.active_effect][0]
        state["current_jutsu"] = jutsu_name
        state["status_text"] = f"ACTIVE: {jutsu_name.upper()}"
    elif recognizer.current_gesture:
        state["current_jutsu"] = recognizer.current_gesture
        state["status_text"] = "FOCUSING CHAKRA..."
    else:
        state["current_jutsu"] = ""
        state["status_text"] = "Ready"

    # Encode result → JPEG → return
    ret, buffer = cv2.imencode('.jpg', result, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ret:
        return Response(status=500)

    return Response(buffer.tobytes(), mimetype='image/jpeg')

# ---------------------------------------------------------------------------
# Status route (used by frontend to poll jutsu state for HUD / cards)
# ---------------------------------------------------------------------------
@app.route('/api/status')
def status():
    session_id = request.headers.get('X-Session-ID', 'default')
    with sessions_lock:
        state = sessions.get(session_id, {})
    return jsonify({
        "current_jutsu": state.get("current_jutsu", ""),
        "status_text": state.get("status_text", "Ready"),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
