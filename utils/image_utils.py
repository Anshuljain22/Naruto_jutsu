import cv2
import numpy as np

def additive_blend(bg_img, fg_img, center_x, center_y, scale=1.0, alpha=1.0):
    """
    Blends an image adaptively onto the background using additive blending.
    Assumes fg_img has a black background.
    """
    if scale != 1.0:
        h, w = fg_img.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        if new_w <= 0 or new_h <= 0:
            return bg_img
        fg_img = cv2.resize(fg_img, (new_w, new_h))
    
    fh, fw = fg_img.shape[:2]
    bh, bw = bg_img.shape[:2]
    
    # Calculate top-left coordinates based on center
    x = int(center_x - fw / 2)
    y = int(center_y - fh / 2)
    
    # Calculate bounds
    y1, y2 = max(0, y), min(bh, y + fh)
    x1, x2 = max(0, x), min(bw, x + fw)
    
    # Calculate corresponding indices in the foreground image
    y1_f = max(0, -y)
    y2_f = y1_f + (y2 - y1)
    
    x1_f = max(0, -x)
    x2_f = x1_f + (x2 - x1)
    
    # If out of bounds completely, just return
    if y1 >= y2 or x1 >= x2:
        return bg_img
        
    bg_roi = bg_img[y1:y2, x1:x2]
    fg_roi = fg_img[y1_f:y2_f, x1_f:x2_f]
    
    # Convert BGR to float32 for blending
    bg_roi_f = bg_roi.astype(np.float32)
    fg_roi_f = fg_roi.astype(np.float32) * alpha
    
    # Additive blend: simply add pixel values, then clip to 255
    blended = np.clip(bg_roi_f + fg_roi_f, 0, 255).astype(np.uint8)
    
    bg_img[y1:y2, x1:x2] = blended
    return bg_img
