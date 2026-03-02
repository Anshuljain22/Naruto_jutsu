import cv2
import time
from input.camera import Camera
from pose_detection.detector import PoseDetector
from gesture_engine.recognizer import GestureRecognizer
from effects.manager import EffectManager

def main():
    print("Initializing Jutsu Vision AR Engine...")

    # Initialize modules
    camera = Camera(camera_id=0, width=1280, height=720)
    detector = PoseDetector(detection_con=0.6, track_con=0.6)
    recognizer = GestureRecognizer()
    effect_manager = EffectManager()

    camera.start()
    time.sleep(1.0) # Warm up

    prev_time = time.time()
    print("Camera started. Perform the Shadow Clone sign (cross forearms). Press 'q' to quit.")

    while True:
        ret, frame = camera.read()
        if not ret or frame is None:
            continue

        # Resize for faster processing if needed, but we requested 1280x720. 
        # MediaPipe scales it internally.

        # Process frame for landmarks and mask
        # We don't draw landmarks by default to keep the AR effect clean
        detector.find_landmarks(frame, draw=False)
        pose_lms = detector.get_pose_landmarks(frame.shape)
        hands_lms = detector.get_hand_landmarks(frame.shape)
        mask = detector.get_segmentation_mask()

        # Detect gesture
        jutsu_triggered = recognizer.detect(pose_lms, hands_lms, frame.shape)
        
        # Trigger effect if newly detected
        if jutsu_triggered:
            effect_manager.trigger(jutsu_triggered, frame, pose_lms, mask)

        # Update and Render Effects
        effect_manager.update()
        
        # Create a display copy for the UI and effects
        display_frame = frame.copy()
        display_frame = effect_manager.render(display_frame)

        # Calculate FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time

        # UI Overlay
        cv2.putText(display_frame, f"FPS: {int(fps)}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Status text
        status_text = "Ready"
        if effect_manager.active_effect:
            # Active jutsu name
            active_name = [k for k, v in effect_manager.effects.items() if v == effect_manager.active_effect][0]
            status_text = f"ACTIVE: {active_name.upper()}"
            cv2.putText(display_frame, status_text, (10, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        elif recognizer.current_gesture:
            status_text = f"DETECTING: {recognizer.current_gesture.upper()}"
            cv2.putText(display_frame, status_text, (10, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

        # Show frame
        cv2.imshow('Naruto Jutsu Vision AR Engine', display_frame)

        # Handle keypresses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    # Clean up
    print("Shutting down...")
    camera.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
