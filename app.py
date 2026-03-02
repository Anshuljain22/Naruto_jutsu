import cv2
import time
import threading
from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
import queue

from input.camera import Camera
from pose_detection.detector import PoseDetector
from gesture_engine.recognizer import GestureRecognizer
from effects.manager import EffectManager

app = Flask(__name__)
CORS(app)

# Global instances (initialized in start_engine)
camera = None
detector = None
recognizer = None
effect_manager = None
engine_running = False

# We'll share the latest processed frame via a thread-safe variable or lock
latest_frame = None
latest_frame_lock = threading.Lock()
current_jutsu = ""
current_status = "Ready"

def init_engine():
    global camera, detector, recognizer, effect_manager
    print("Initializing Jutsu Vision AR Engine (Backend Mode)...")
    camera = Camera(camera_id=0, width=1280, height=720)
    detector = PoseDetector(detection_con=0.6, track_con=0.6)
    recognizer = GestureRecognizer()
    effect_manager = EffectManager()
    
def run_ar_engine():
    global camera, detector, recognizer, effect_manager, engine_running
    global latest_frame, current_jutsu, current_status
    
    # Always create fresh instances so restart works cleanly
    init_engine()
        
    if not camera.start():
        print("Error: Could not start camera.")
        engine_running = False
        return

    time.sleep(1.0) # Warm up
    prev_time = time.time()
    
    print("Engine loop started.")

    try:
        while engine_running:
            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
                
            detector.find_landmarks(frame, draw=False)
            pose_lms = detector.get_pose_landmarks(frame.shape)
            hands_lms = detector.get_hand_landmarks(frame.shape)
            mask = detector.get_segmentation_mask()
            
            jutsu_triggered = recognizer.detect(pose_lms, hands_lms, frame.shape)
            
            if jutsu_triggered:
                effect_manager.trigger(jutsu_triggered, frame, pose_lms, mask)
                
            effect_manager.update()
            display_frame = frame.copy()
            display_frame = effect_manager.render(display_frame)
            
            # Calculate FPS
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time
            
            # Update shared state
            status_text = "Ready"
            jutsu_name = ""
            
            if effect_manager.active_effect:
                jutsu_name = [k for k, v in effect_manager.effects.items() if v == effect_manager.active_effect][0]
                status_text = f"ACTIVE: {jutsu_name.upper()}"
            elif recognizer.current_gesture:
                jutsu_name = recognizer.current_gesture
                status_text = f"FOCUSING CHAKRA..."
                
            current_jutsu = jutsu_name
            current_status = status_text
            
            # Encode to JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret:
                with latest_frame_lock:
                    latest_frame = buffer.tobytes()
    except Exception as e:
        print(f"Engine Loop Crashed: {e}")

    print("Engine loop stopped.")
    engine_running = False
    camera.stop()

def generate_frames():
    """Generator function that yields JPEG frames for MJPEG streaming."""
    while True: # Keep generator alive even when engine stops, just yield blanks/waiting image
        if not engine_running:
            time.sleep(0.5)
            continue
            
        with latest_frame_lock:
            frame = latest_frame
        
        if frame is None:
            time.sleep(0.01)
            continue
            
        # Yield the multipart payload
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.01) # Approx 60fps limit to prevent spam

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/api/status')
def status():
    """Returns the current state of the engine."""
    return jsonify({
        "running": engine_running,
        "current_jutsu": current_jutsu,
        "status_text": current_status
    })

@app.route('/api/start', methods=['POST'])
def start_engine():
    """Starts the background camera and processing thread."""
    global engine_running
    if not engine_running:
        engine_running = True
        thread = threading.Thread(target=run_ar_engine, daemon=True)
        thread.start()
        return jsonify({"message": "Engine starting"}), 200
    return jsonify({"message": "Engine already running"}), 200

@app.route('/api/stop', methods=['POST'])
def stop_engine():
    """Stops the engine safely."""
    global engine_running
    engine_running = False
    return jsonify({"message": "Engine stopping"}), 200

@app.route('/video_feed')
def video_feed():
    """Route for the MJPEG stream. Attach to <img src="...">"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Using threaded=True helps serve the MJPEG stream without blocking API requests
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
