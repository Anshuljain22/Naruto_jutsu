import time
import cv2
import numpy as np
import os

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets')

class FireballEffect:
    def __init__(self, duration=4.0):
        self.duration = duration
        self.start_time = 0.0
        self.is_active = False
        self.mouth_x = 0
        self.mouth_y = 0
        self.sprite = cv2.imread(os.path.join(_ASSET_DIR, 'fireball.png'))

    def trigger(self, frame, pose_lms, mask):
        self.start_time = time.time()
        self.is_active = True
        self.update_position(frame, pose_lms)

    def update_position(self, frame, pose_lms):
        if not pose_lms:
            return
            
        h, w, _ = frame.shape
        p_dict = {lm[0]: (lm[1], lm[2]) for lm in pose_lms}
        
        NOSE = 0
        if NOSE in p_dict:
            self.mouth_x = int(p_dict[NOSE][0])
            self.mouth_y = int(p_dict[NOSE][1]) + 20
        else:
            self.mouth_x = w // 2
            self.mouth_y = h // 2

    def update(self, frame=None, pose_lms=None):
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
        if not self.is_active or self.sprite is None:
            return frame
            
        elapsed = time.time() - self.start_time
        result = frame.copy()
        
        progress = elapsed / self.duration
        growth_phase = min(1.0, elapsed / 1.0)
        
        scale = 0.1 + (1.4 * growth_phase)
        
        if elapsed > 1.0:
            shoot_progress = (elapsed - 1.0) / (self.duration - 1.0)
            scale += shoot_progress * 3.0
            
        alpha = 1.0
        if self.duration - elapsed < 1.0:
             alpha = max(0.0, self.duration - elapsed)
             
        if growth_phase < 1.0:
             scale *= np.random.uniform(0.9, 1.1)
        
        y_offset = int(self.mouth_y)
        if elapsed > 1.0:
             y_offset -= int(((elapsed - 1.0) * 400))
             
        from utils.image_utils import additive_blend
        result = additive_blend(result, self.sprite, self.mouth_x, y_offset, scale=scale, alpha=alpha)
        
        return result
