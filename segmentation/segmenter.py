import cv2
import numpy as np

class Segmenter:
    def __init__(self):
        # We will use the mask from our PoseDetector directly for performance
        pass

    def apply_background_transparency(self, frame, mask):
        """
        Takes the current frame and the MediaPipe segmentation mask.
        Returns a frame where the background is transparent (alpha channel = 0),
        or replaced with green/black depending on what's needed for cloning.
        """
        if mask is None:
            return frame

        # Mask returned by Tasks API might be (H, W, 1), squeeze to (H, W)
        if len(mask.shape) == 3:
            mask = mask.squeeze(-1)

        # Mask is a float32 array with values in [0.0, 1.0].
        # We create a binary mask. Subject > 0.5 is foreground.
        condition = np.stack((mask,) * 3, axis=-1) > 0.5

        # Create a blank image with 0 (black background) or transparent
        # We use BGR for OpenCV mostly, let's keep it black for the background
        # or we can extract just the person
        bg_image = np.zeros(frame.shape, dtype=np.uint8)
        
        # Where condition is true, use frame, else bg_image
        output_image = np.where(condition, frame, bg_image)
        
        return output_image

    def extract_person_rgba(self, frame, mask):
        """
        Extracts the person and returns an RGBA image where background is transparent.
        """
        if mask is None:
            # Return fully opaque frame if no mask
            return cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

        # Mask returned by Tasks API might be (H, W, 1)
        if len(mask.shape) == 3:
            mask = mask.squeeze(-1)

        # Convert frame to BGRA
        frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        
        # Condition > 0.5 is foreground
        alpha_channel = (mask > 0.5).astype(np.uint8) * 255
        
        # Replace alpha
        frame_bgra[:, :, 3] = alpha_channel
        
        return frame_bgra
