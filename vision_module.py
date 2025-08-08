# vision_module.py
# Version 5.1: Game Detection Fix
# Reverts the is_game_active function to a more reliable full-screen
# check to ensure it always finds the game HUD before calibration.

import mss
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO

class Vision:
    def __init__(self):
        self.sct = mss.mss()
        self.model = YOLO("yolov8n.pt")
        self.game_window = None
        self.scaled_rois = {}
        self.base_resolution = (1920, 1080)
        self.ui_map = { "HUD_ELEMENTS": { "COMPASS": (600, 50, 720, 50), "HORIZON": (0, 300, 1920, 480) } }
        self.hud_color_ranges = { "green_amber": ([20, 100, 100], [40, 255, 255]), "white": ([0, 0, 180], [180, 30, 255]), "blue": ([100, 150, 150], [130, 255, 255]) }
        print("Vision module initialized, awaiting calibration.")

    def calibrate(self, monitor_number=1):
        monitor = self.sct.monitors[monitor_number]
        self.game_window = monitor
        self._scale_rois()
        print(f"Calibration successful. Game window set to: {self.game_window}")

    def _scale_rois(self):
        scaled = {}
        base_w, base_h = self.base_resolution
        current_w, current_h = self.game_window['width'], self.game_window['height']
        scale_x = current_w / base_w
        scale_y = current_h / base_h
        for name, roi in self.ui_map["HUD_ELEMENTS"].items():
            x, y, w, h = roi
            scaled[name] = { "left": self.game_window['left'] + int(x * scale_x), "top": self.game_window['top'] + int(y * scale_y), "width": int(w * scale_x), "height": int(h * scale_y) }
        self.scaled_rois = scaled

    def capture_roi_image(self, region_name):
        if region_name not in self.scaled_rois: return None
        roi = self.scaled_rois[region_name]
        sct_img = self.sct.grab(roi)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def analyze_image(self, img):
        results = self.model(img, verbose=False)
        detections = []
        img_width = img.width
        for result in results:
            for box in result.boxes:
                class_name = self.model.names[int(box.cls[0])]
                bounding_box = box.xyxy[0].cpu().numpy()
                x_center = (bounding_box[0] + bounding_box[2]) / 2
                box_width = bounding_box[2] - bounding_box[0]
                if x_center < img_width * 0.33: position = "on the left"
                elif x_center > img_width * 0.66: position = "on the right"
                else: position = "in the center"
                relative_width = box_width / img_width
                if relative_width > 0.4: size = "very large (close)"
                elif relative_width > 0.2: size = "large (medium distance)"
                else: size = "small (far away)"
                detections.append({ "label": class_name, "position": position, "size": size })
        return detections

    def is_game_active(self):
        """
        FIX: This function now reliably checks the primary monitor to find the game.
        """
        try:
            # Grab the primary monitor (monitor 1)
            monitor = self.sct.monitors[1]
            sct_img = self.sct.grab(monitor)

            # Convert to an image format that OpenCV can read
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            cv_image = np.array(img)
            hsv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2HSV)

            # Check for any of our known HUD colors
            for color_name, (lower, upper) in self.hud_color_ranges.items():
                mask = cv2.inRange(hsv_image, np.array(lower), np.array(upper))
                # We check for a very small percentage, as the HUD is only a tiny part of the screen
                if (cv2.countNonZero(mask) / mask.size) * 100 > 0.1:
                    print(f"Game detected based on '{color_name}' HUD color.")
                    return True
        except Exception as e:
            print(f"Error during game detection: {e}")
            return False

        # If no colors match after checking the whole screen, the game is not active
        return False

    def close(self):
        self.sct.close()
