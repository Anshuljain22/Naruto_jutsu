import time
import cv2
import numpy as np
import random
import os

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets')

class RasenganEffect:
    def __init__(self, duration=5.0):
        self.duration = duration
        self.start_time = 0.0
        self.is_active = False
        
        # Center of the hands where rasengan will form
        self.center_x = 0
        self.center_y = 0

    def trigger(self, frame, pose_lms, mask):
        """Called once when the jutsu is detected."""
        self.start_time = time.time()
        self.is_active = True
        
        # Determine the initial center of the Rasengan based on hand position
        # We need wrists to find the center point
        h, w, c = frame.shape
        p_dict = {lm[0]: (lm[1], lm[2]) for lm in pose_lms}
        
        # Fallback to center of screen if tracking fails immediately
        self.center_x = w // 2
        self.center_y = h // 2
        
        # Left Wrist = 15, Right Wrist = 16 (BlazePose)
        L_WRIST = 15
        R_WRIST = 16
        
        if L_WRIST in p_dict and R_WRIST in p_dict:
            lw = p_dict[L_WRIST]
            rw = p_dict[R_WRIST]
            self.center_x = int((lw[0] + rw[0]) / 2)
            self.center_y = int((lw[1] + rw[1]) / 2)

    def update(self):
        """Returns True if the effect is still active, False if finished."""
        if not self.is_active:
            return False
            
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.is_active = False
            return False
        
        return True

    def render(self, frame):
        """Renders the Rasengan over the live frame."""
        if not self.is_active:
            return frame
            
        elapsed = time.time() - self.start_time
        
        # Animation variables
        # Grow slowly over the first 2.0s, shrink at the end
        progress = min(1.0, elapsed / 2.0)
        fade_out = 1.0
        if self.duration - elapsed < 0.5:
            fade_out = max(0.0, (self.duration - elapsed) / 0.5)
            
        max_radius = 80
        current_radius = int(max_radius * progress * fade_out)
        
        if current_radius <= 0:
            return frame
            
        result = frame.copy()
        
        if not hasattr(self, 'sprite'):
            self.sprite = cv2.imread(os.path.join(_ASSET_DIR, 'rasengan.png'))
            if self.sprite is None:
                cv2.circle(result, (self.center_x, self.center_y), current_radius, (255, 255, 200), -1)
                return result
                
        # Scale based on progress (growing from hands)
        # Using a larger max scale for a dramatic finish
        base_scale = 0.45 
        
        # Add a pulsating effect that gets tighter as it stabilizes
        # High jitter early on, low jitter later
        pulse = random.uniform(0.9, 1.1) if progress < 1.0 else random.uniform(0.98, 1.02)
        scale = base_scale * progress * pulse * fade_out
        
        # Spin faster as it builds up (from chaotic to smooth)
        h, w = self.sprite.shape[:2]
        center = (w // 2, h // 2)
        
        # Exponential spin: starts slow, goes very fast as it reaches 1.0
        spin_speed = 360 * (1.0 + progress * 3) # Starts at 1 rot/s, goes up to 4 rot/s
        angle = (elapsed * spin_speed) % 360
        
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_sprite = cv2.warpAffine(self.sprite, M, (w, h), flags=cv2.INTER_LINEAR)
        
        from utils.image_utils import additive_blend
        
        # Fade in curve (opacity starts low and builds up with progress)
        alpha = progress * fade_out
        result = additive_blend(result, rotated_sprite, self.center_x, self.center_y, scale=scale, alpha=alpha)
        
        return result
