import cv2
import mediapipe as mp
import os

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Absolute paths so the models are found regardless of CWD
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class PoseDetector:
    def __init__(self, mode=False, max_hands=2, detection_con=0.5, track_con=0.5):
        pose_model_path = os.path.join(_BASE_DIR, 'models', 'pose_landmarker_lite.task')
        hand_model_path = os.path.join(_BASE_DIR, 'models', 'hand_landmarker.task')

        # IMAGE mode: each frame processed independently — works perfectly with
        # variable-rate browser frame submissions (no monotonic timestamp needed).
        pose_options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=pose_model_path),
            running_mode=VisionRunningMode.IMAGE,
            output_segmentation_masks=True,
            min_pose_detection_confidence=detection_con,
        )
        self.pose_landmarker = PoseLandmarker.create_from_options(pose_options)

        hand_options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=hand_model_path),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_con,
        )
        self.hand_landmarker = HandLandmarker.create_from_options(hand_options)

        self.pose_result = None
        self.hand_result = None

    def find_landmarks(self, img, draw=False):
        """Processes the image and finds pose + hand landmarks."""
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

        # IMAGE mode uses detect() not detect_for_video()
        self.pose_result = self.pose_landmarker.detect(mp_image)
        self.hand_result = self.hand_landmarker.detect(mp_image)
        return img

    def get_pose_landmarks(self, img_shape):
        """Returns a list of pose landmarks [id, x, y, z] in pixel coords."""
        lm_list = []
        if self.pose_result and self.pose_result.pose_landmarks:
            h, w, c = img_shape
            for id, lm in enumerate(self.pose_result.pose_landmarks[0]):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy, lm.z])
        return lm_list

    def get_hand_landmarks(self, img_shape):
        """Returns a list of hands, each hand a list of [id, x, y, z]."""
        hands_list = []
        if self.hand_result and self.hand_result.hand_landmarks:
            h, w, c = img_shape
            for hand_lms in self.hand_result.hand_landmarks:
                hand_points = []
                for id, lm in enumerate(hand_lms):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    hand_points.append([id, cx, cy, lm.z])
                hands_list.append(hand_points)
        return hands_list

    def get_segmentation_mask(self):
        """Returns the segmentation mask as a numpy array, or None."""
        if self.pose_result and self.pose_result.segmentation_masks:
            return self.pose_result.segmentation_masks[0].numpy_view()
        return None
