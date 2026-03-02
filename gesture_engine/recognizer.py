import time
from utils.math_utils import get_distance, get_angle
import mediapipe as mp

class GestureRecognizer:
    def __init__(self):
        # MediaPipe landmark indices (BlazePose topology)
        self.L_SHOULDER = 11
        self.R_SHOULDER = 12
        self.L_ELBOW = 13
        self.R_ELBOW = 14
        self.L_WRIST = 15
        self.R_WRIST = 16
        
        # State tracking for sustained gestures
        self.current_gesture: str | None = None
        self.gesture_start_time = 0.0
        self.hold_threshold = 0.5 # Seconds to hold a gesture to trigger

        # Velocity tracking (for Chidori/Wind Push)
        self.prev_wrist_r = None
        self.prev_wrist_l = None
        self.prev_time = time.time()

    def detect(self, pose_lms, hands_lms, img_shape):
        """
        Analyzes landmarks and returns the detected gesture string, 
        or None if no specific gesture is recognized for the required duration.
        """
        h, w, c = img_shape
        detected = None
        curr_time = time.time()

        # Need pose landmarks for most jutsus
        if not pose_lms:
            return None

        # Convert pose list to dictionary for easier access by ID
        # Landmark format: [id, x, y, z]
        p_dict = {lm[0]: (lm[1], lm[2]) for lm in pose_lms}

        if self._is_shadow_clone(hands_lms, p_dict):
            detected = "shadow_clone"
        elif self._is_rasengan(hands_lms, p_dict):
            detected = "rasengan"
        elif self._is_fireball(hands_lms, p_dict, h, w):
            detected = "fireball"
        elif self._is_chidori(hands_lms):
            detected = "chidori"

        # Update tracking for sustained gestures
        if detected:
            if self.current_gesture == detected:
                if (curr_time - self.gesture_start_time) >= self.hold_threshold:
                    return detected
            else:
                self.current_gesture = detected
                self.gesture_start_time = curr_time
        else:
            self.current_gesture = None

        return None

    def _is_shadow_clone(self, hands_lms, p_dict):
        """
        Detects Shadow Clone Jutsu (Plus/Cross sign with index fingers).
        """
        if not hands_lms or len(hands_lms) < 2:
            return False
            
        h1 = hands_lms[0]
        h2 = hands_lms[1]
        
        # Check distance between index knuckles
        h1_idx_mcp = (h1[5][1], h1[5][2])
        h2_idx_mcp = (h2[5][1], h2[5][2])
        m_dist = get_distance(h1_idx_mcp, h2_idx_mcp)
        
        try:
            l_shldr = p_dict[self.L_SHOULDER]
            r_shldr = p_dict[self.R_SHOULDER]
            shoulder_dist = get_distance(l_shldr, r_shldr)
            
            # Index knuckles should be relatively close to form the cross seal
            if shoulder_dist > 0 and m_dist < shoulder_dist * 0.8:
                def get_idx_vec(h):
                    mcp = h[5]
                    tip = h[8]
                    vec = (tip[1] - mcp[1], tip[2] - mcp[2])
                    mag = (vec[0]**2 + vec[1]**2)**0.5
                    if mag == 0: return (1, 0)
                    return (vec[0]/mag, vec[1]/mag)
                    
                v1 = get_idx_vec(h1)
                v2 = get_idx_vec(h2)
                
                # Dot product
                dot = abs(v1[0]*v2[0] + v1[1]*v2[1])
                
                # Near perpendicular (cross sign)
                # dot < 0.75 means roughly between 40 and 140 degrees
                if dot < 0.75: 
                    return True
        except KeyError:
            pass
            
        return False

    def _is_rasengan(self, hands_lms, p_dict):
        """
        Detects Rasengan (Both hands forming a sphere shape close to each other).
        """
        if not hands_lms or len(hands_lms) < 2:
            return False

        h1 = hands_lms[0]
        h2 = hands_lms[1]
        
        # Index 0 is WRIST for hands
        h1_wrist = (h1[0][1], h1[0][2])
        h2_wrist = (h2[0][1], h2[0][2])

        dist = get_distance(h1_wrist, h2_wrist)

        try:
            l_shldr = p_dict[self.L_SHOULDER]
            r_shldr = p_dict[self.R_SHOULDER]
            shoulder_dist = get_distance(l_shldr, r_shldr)
            
            if shoulder_dist > 0 and (shoulder_dist * 0.6 < dist < shoulder_dist * 1.5):
                # We also expect the wrists to be somewhat horizontally aligned
                y_dist = abs(h1_wrist[1] - h2_wrist[1])
                # Hands should be roughly at the same height for Rasengan
                if y_dist < shoulder_dist * 0.6:
                    return True
        except KeyError:
            pass

        return False
    def _is_chidori(self, hands_lms):
        """
        Detects Chidori (Claw hand facing camera).
        """
        if not hands_lms:
            return False

        for hand in hands_lms:
            h_dict = {lm[0]: (lm[1], lm[2], lm[3]) for lm in hand}
            
            # Knuckles (MCP) and Tips
            idx_mcp, idx_tip = h_dict[5], h_dict[8]
            mid_mcp, mid_tip = h_dict[9], h_dict[12]
            wrist = h_dict[0]
            
            def dist2d(p1, p2):
                return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                
            palm_size = dist2d(wrist, mid_mcp)
            if palm_size == 0:
                continue
                
            idx_ratio = dist2d(idx_mcp, idx_tip) / palm_size
            mid_ratio = dist2d(mid_mcp, mid_tip) / palm_size
            
            idx_z_diff = idx_tip[2] - wrist[2]
            mid_z_diff = mid_tip[2] - wrist[2]
            
            # Claw facing camera: 
            # 1. Foreshortening causes 2D distance from knuckle to tip to be small/medium (0.1 to 0.75)
            # 2. Z coordinates of tips are closer to camera (negative difference compared to wrist)
            if 0.1 < idx_ratio < 0.8 and 0.1 < mid_ratio < 0.8:
                if idx_z_diff < -0.02 and mid_z_diff < -0.02:
                    return True
                    
        return False

    def _is_fireball(self, hands_lms, p_dict, h, w):
        """
        Detects Fireball Jutsu (Two fingers on lips).
        """
        if not hands_lms:
            return False
            
        NOSE = 0
        if NOSE not in p_dict:
            return False
            
        nose = p_dict[NOSE]
        
        # Approximate mouth position just below the nose
        # p_dict values are already pixel coordinates (converted in detector.py)
        mouth_x = nose[0]
        mouth_y = nose[1] + 20
        
        for hand in hands_lms:
            h_dict = {lm[0]: (lm[1], lm[2], lm[3]) for lm in hand}
            
            idx_tip = h_dict[8]
            mid_tip = h_dict[12]
            ring_tip = h_dict[16]
            wrist = h_dict[0]
            
            def dist2d(p1, p2):
                return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                
            # Hand landmark coords from h_dict are also pixel values
            idx_dist = dist2d((idx_tip[0], idx_tip[1]), (mouth_x, mouth_y))
            mid_dist = dist2d((mid_tip[0], mid_tip[1]), (mouth_x, mouth_y))
            
            try:
                l_shldr = p_dict[self.L_SHOULDER]
                r_shldr = p_dict[self.R_SHOULDER]
                shoulder_width = dist2d((l_shldr[0], l_shldr[1]), (r_shldr[0], r_shldr[1]))
                
                # Fingers close to mouth (within 35% of shoulder width)
                if idx_dist < shoulder_width * 0.35 or mid_dist < shoulder_width * 0.35:
                    
                    # Ensure index and middle are somewhat extended, while ring is curled
                    idx_wrist_dist = dist2d(idx_tip, wrist)
                    ring_wrist_dist = dist2d(ring_tip, wrist)
                    
                    if ring_wrist_dist < idx_wrist_dist * 0.85:
                        return True
            except KeyError:
                pass
                
        return False
