import cv2
import time
import threading

class Camera:
    def __init__(self, camera_id=0, width=1280, height=720):
        self.camera_id = camera_id
        self.width = width
        self.height = height

        self.cap = None
        self.ret = False
        self.frame = None
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        """Open the camera and start the background read thread. Returns True on success."""
        # Re-open VideoCapture every time start() is called (supports restart after stop)
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_id}.")
            return False

        self.frame = None
        self.ret = False
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        return True

    def _update(self):
        """Continuously loop to get the latest frame."""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            with self.lock:
                self.ret = ret
                # Flip the frame horizontally for a more intuitive selfie-view
                self.frame = cv2.flip(frame, 1)

    def read(self):
        """Return the most recent frame."""
        with self.lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return self.ret, None

    def stop(self):
        """Stop the background thread and release resources."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        self.cap.release()
