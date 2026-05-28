"""Image recognition engine using OpenCV template matching."""
import cv2
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

class ImageRecognition:
    """Template matching and OCR for Arknights game screen analysis."""

    def __init__(self, assets_dir='assets/images'):
        self.assets_dir = assets_dir
        self._template_cache = {}

    def load_template(self, name):
        """Load and cache a template image."""
        if name in self._template_cache:
            return self._template_cache[name]
        path = os.path.join(self.assets_dir, f'{name}.png')
        if not os.path.exists(path):
            logger.warning(f'Template not found: {path}')
            return None
        template = cv2.imread(path, cv2.IMREAD_COLOR)
        self._template_cache[name] = template
        return template

    def find_template(self, screen, template_name, threshold=0.8):
        """Find a template on screen. Returns (x, y, confidence) or None."""
        template = self.load_template(template_name)
        if template is None:
            return None

        # Convert to BGR if needed
        if len(screen.shape) == 2:
            screen = cv2.cvtColor(screen, cv2.COLOR_GRAY2BGR)

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y, max_val)
        return None

    def find_all_templates(self, screen, template_name, threshold=0.8):
        """Find all occurrences of a template on screen."""
        template = self.load_template(template_name)
        if template is None:
            return []

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        h, w = template.shape[:2]

        matches = []
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            confidence = result[pt[1], pt[0]]
            matches.append((center_x, center_y, confidence))

        # Remove overlapping matches
        return self._non_max_suppression(matches, min_dist=max(w, h) // 2)

    def wait_for_template(self, capture_func, template_name, timeout=10, threshold=0.8, interval=0.5):
        """Wait for a template to appear on screen."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            screen = capture_func()
            result = self.find_template(screen, template_name, threshold)
            if result:
                return result
            time.sleep(interval)
        return None

    def compare_images(self, img1, img2):
        """Compare two images, return similarity score (0-1)."""
        if img1.shape != img2.shape:
            return 0.0
        diff = cv2.absdiff(img1, img2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        score = 1.0 - (np.mean(gray) / 255.0)
        return score

    def crop_region(self, image, x1, y1, x2, y2):
        """Crop a region from image."""
        return image[y1:y2, x1:x2]

    def find_color(self, screen, target_bgr, tolerance=30):
        """Find pixels matching a target color. Returns list of (x, y) positions."""
        lower = np.array([max(0, c - tolerance) for c in target_bgr])
        upper = np.array([min(255, c + tolerance) for c in target_bgr])
        mask = cv2.inRange(screen, lower, upper)
        locations = np.column_stack(np.where(mask > 0))
        return [(int(p[1]), int(p[0])) for p in locations]

    def get_pixel_color(self, screen, x, y):
        """Get the BGR color at a specific pixel."""
        return tuple(int(c) for c in screen[y, x])

    def _non_max_suppression(self, matches, min_dist=50):
        """Remove overlapping matches within min_dist pixels."""
        if not matches:
            return []
        matches.sort(key=lambda m: m[2], reverse=True)
        filtered = []
        for match in matches:
            too_close = False
            for existing in filtered:
                dist = ((match[0] - existing[0])**2 + (match[1] - existing[1])**2)**0.5
                if dist < min_dist:
                    too_close = True
                    break
            if not too_close:
                filtered.append(match)
        return filtered
