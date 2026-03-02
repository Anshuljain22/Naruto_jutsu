import time
import cv2
import numpy as np
import random
import os

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets')

class ChidoriEffect:
    def __init__(self, duration=3.0):
        self.duration = duration
        self.start_time = 0.0
        self.is_active = False
        
        # Target wrist to attach the lightning
        self.target_wrist_x = 0
        self.target_wrist_y = 0
        
    def trigger(self, frame, pose_lms, mask):
        """Called once when the jutsu is detected."""
        self.start_time = time.time()
        self.is_active = True
        
        # Initial position
        self.update_position(frame, pose_lms)

    def update_position(self, frame, pose_lms):
        """Update the center of the effect based on the thrusting hand."""
        if not pose_lms:
            return

        h, w, c = frame.shape
        p_dict = {lm[0]: (lm[1], lm[2]) for lm in pose_lms}
        
        # We usually assume the thrusting hand is the one further forward or moving fastest.
        # Since we just triggered it, we'll look for the wrist that is generally higher (lower Y) 
        # or just pick the right wrist as default for Chidori for simplicity.
        
        L_WRIST = 15
        R_WRIST = 16
        
        # Let's attach to the hand that is highest in the frame (lowest Y value)
        # Assuming the thrusting hand is raised
        lw = p_dict.get(L_WRIST)
        rw = p_dict.get(R_WRIST)
        
        if lw and rw:
            if lw[1] < rw[1]:
                self.target_wrist_x = int(lw[0])
                self.target_wrist_y = int(lw[1])
            else:
                self.target_wrist_x = int(rw[0])
                self.target_wrist_y = int(rw[1])
        elif lw:
            self.target_wrist_x = int(lw[0])
            self.target_wrist_y = int(lw[1])
        elif rw:
            self.target_wrist_x = int(rw[0])
            self.target_wrist_y = int(rw[1])

    def update(self, frame=None, pose_lms=None):
        """Returns True if the effect is still active. Also updates position if pose provided."""
        if not self.is_active:
            return False
            
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.is_active = False
            return False
            
        if frame is not None and pose_lms is not None:
             self.update_position(frame, pose_lms)
        
        return True

    def render(self, frame):
        """Renders the Chidori lightning effect over the live frame."""
        if not self.is_active:
            return frame
            
        elapsed = time.time() - self.start_time
        
        # Fade out at the end
        fade_out = 1.0
        if self.duration - elapsed < 0.5:
            fade_out = max(0.0, (self.duration - elapsed) / 0.5)
            
        if fade_out <= 0:
            return frame
            
        result = frame.copy()
        
        # We need an image loaded
        if not hasattr(self, 'sprite'):
            self.sprite = cv2.imread(os.path.join(_ASSET_DIR, 'chidori.png'))
            if self.sprite is None:
                # Fallback
                cv2.circle(result, (self.target_wrist_x, self.target_wrist_y), 40, (255, 200, 50), -1) 
                return result
                
        # Scale the sprite randomly a little bit to give it a pulsating feel
        scale = random.uniform(0.8, 1.2) * (1.0 if elapsed > 0.3 else elapsed / 0.3)
        
        # Additive blend image onto frame
        from utils.image_utils import additive_blend
        result = additive_blend(result, self.sprite, self.target_wrist_x, self.target_wrist_y, scale=scale, alpha=fade_out)
        
        return result
