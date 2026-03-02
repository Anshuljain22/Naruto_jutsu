import time
import cv2
import numpy as np
from segmentation.segmenter import Segmenter

class ShadowCloneEffect:
    def __init__(self, duration=3.0):
        self.duration = duration
        self.start_time = 0.0
        self.is_active = False
        
        self.segmenter = Segmenter()
        self.clone_mask = None
        self.clone_rgba = None
        
        self.clones_count = 2 # 1 left, 1 right
    
    def trigger(self, frame, pose_lms, mask):
        """Called once when the jutsu is detected."""
        self.start_time = time.time()
        self.is_active = True
        
        # Save a snapshot of the person for clones
        bgr_frame = frame.copy()
        
        if mask is not None:
             # Get the segmentation mask
             self.clone_rgba = self.segmenter.extract_person_rgba(bgr_frame, mask)
        else:
             # Fallback
             self.clone_rgba = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2BGRA)

    def update(self):
        """Returns True if the effect is still active, False if finished."""
        if not self.is_active:
            return False
            
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.is_active = False
            self.clone_rgba = None
            return False
        
        return True

    def render(self, frame):
        """Renders clones over the live frame using alpha blending."""
        if not self.is_active or self.clone_rgba is None:
            return frame
            
        elapsed = time.time() - self.start_time
        
        # Animation variables
        # ease out from original position
        # max offset is e.g. 200 pixels
        max_offset = 300
        progress = min(1.0, elapsed / 0.5) # completes animation in 0.5 seconds
        
        # simple ease out
        eased_progress = 1 - (1 - progress) ** 3
        current_offset = int(max_offset * eased_progress)

        # Alpha handling (fade out at the end)
        alpha_scale = 1.0
        if self.duration - elapsed < 0.5:
            alpha_scale = max(0, (self.duration - elapsed) / 0.5)
            
        return self._overlay_clones(frame, self.clone_rgba, current_offset, alpha_scale)

    def _overlay_clones(self, frame, clone_rgba, offset, alpha_scale):
        """Overlays two clones onto the frame directly using numpy splicing."""
        result = frame.copy()
        h, w, c = result.shape
        
        # The offset shifts the entire image
        # Clone 1: Shift Left
        # We need to take the right part of the clone image and put it on the left part of result
        if offset > 0:
            # Clone LEFT (shifted by -offset on x)
            # The clone is at [:, offset:w] in its own coordinates going to [:, 0:w-offset] in result coords
            if offset < w:
                clone1_crop = clone_rgba[:, offset:]
                base1_crop = result[:, :w-offset]
                result[:, :w-offset] = self._alpha_blend(base1_crop, clone1_crop, alpha_scale)

            # Clone RIGHT (shifted by +offset on x)
            if offset < w:
                clone2_crop = clone_rgba[:, :w-offset]
                base2_crop = result[:, offset:]
                result[:, offset:] = self._alpha_blend(base2_crop, clone2_crop, alpha_scale)

        return result

    def _alpha_blend(self, base_bgr, overlay_rgba, alpha_scale=1.0):
        """Blends an RGBA an overlay onto a BGR image."""
        if base_bgr.shape[:2] != overlay_rgba.shape[:2]:
            return base_bgr
            
        # Overall opacity of clones
        opacity = 0.8 * alpha_scale
            
        alpha_mask = (overlay_rgba[:, :, 3] / 255.0) * opacity
        
        for c in range(3):
            base_bgr[:, :, c] = (alpha_mask * overlay_rgba[:, :, c] + 
                                (1 - alpha_mask) * base_bgr[:, :, c])
        return base_bgr
