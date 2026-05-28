"""ADB controller optimized for MuMu emulator with VLM integration."""
import subprocess
import time
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ADBController:
    """ADB controller with MuMu emulator preset configurations."""

    MUMU_DEFAULTS = {
        'host': '127.0.0.1',
        'port': 16384,
        'resolution': (1280, 720),
    }

    # Arknights package/component (used to force game onto display 0)
    GAME_COMPONENT = 'com.hypergryph.arknights/com.u8.sdk.U8UnityContext'

    def __init__(self, adb_path='adb', host='127.0.0.1', port=16384):
        self.adb_path = adb_path
        self.host = host
        self.port = port
        self.device = f'{host}:{port}'
        self.connected = False
        self._process = None
        self._auto_reconnect = True
        self._reconnect_attempts = 3
        self._last_screenshot = None
        self._game_display = 0  # detected in _detect_display_id()
        # Physical display dimensions (MuMu 12 portrait display)
        self._phys_w = 1080
        self._phys_h = 1920
        # Game landscape dimensions
        self._game_w = 1920
        self._game_h = 1080

    def _run(self, args, timeout=30):
        """Execute an ADB command and return output."""
        cmd = [self.adb_path] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout, result.stderr, result.returncode
        except FileNotFoundError:
            raise RuntimeError(f'ADB not found at: {self.adb_path}')
        except subprocess.TimeoutExpired:
            raise RuntimeError(f'ADB command timed out: {cmd}')

    def _ensure_connected(self):
        """Check connection and auto-reconnect if needed."""
        if self.is_connected():
            return True
        if not self._auto_reconnect:
            return False
        for attempt in range(self._reconnect_attempts):
            logger.warning(f'Connection lost, reconnecting ({attempt+1}/{self._reconnect_attempts})...')
            time.sleep(1)
            self._run(['connect', self.device])
            if self.is_connected():
                logger.info('Reconnected successfully')
                return True
        logger.error('Auto-reconnect failed')
        self.connected = False
        return False

    def connect(self):
        """Connect to MuMu emulator."""
        logger.info(f'Connecting to MuMu at {self.device}...')
        self._run(['connect', self.device])
        stdout, stderr, code = self._run(['-s', self.device, 'get-state'])
        state = stdout.decode().strip()
        if state == 'device':
            self.connected = True
            self._detect_display_id()
            logger.info('MuMu connected successfully')
            return True
        logger.error(f'Connection failed. State: {state}')
        return False

    def _detect_display_id(self):
        """Detect which display the game is on.

        MuMu 12 Hyper-V assigns the game to a separate display (typically #4).
        We do NOT try to force it to display #0 — that conflicts with MuMu's
        display manager. Default screencap already captures the game display.
        The detected display ID is used for ``input -d <id>`` targeting.
        """
        if not self.connected:
            return
        try:
            stdout, _, code = self._run(
                ['-s', self.device, 'shell', 'dumpsys', 'activity', 'activities'],
                timeout=10
            )
            output = stdout.decode('utf-8', errors='ignore')
            current_display = 0
            in_game_display = False
            for line in output.split('\n'):
                stripped = line.strip()
                # "Display #4 (activities from top to bottom):"
                if stripped.startswith('Display #') and 'activities' in stripped:
                    for token in stripped.split():
                        if token.startswith('#') and token[1:].isdigit():
                            current_display = int(token[1:])
                    in_game_display = False
                # Inside a display section, check if arknights is there
                if 'arknights' in stripped.lower() and current_display > 0:
                    self._game_display = current_display
                    logger.info(f'Game is on display #{self._game_display}')
                    return
        except Exception as e:
            logger.debug(f'Display detection skipped: {e}')
        self._game_display = 0

    def _game_to_portrait(self, x, y):
        """Convert landscape game coordinates to ADB portrait coordinates.

        Formula (90° CW rotation inverse):
            x_adb = y_game
            y_adb = 1920 - x_game
        """
        px = y
        py = self._phys_h - x
        return max(0, min(self._phys_w, px)), max(0, min(self._phys_h, py))

    def _input_cmd(self, args, display_id=None):
        """Build an ADB input command.

        If display_id is given, tries ``input -d <id>`` (Android 13+).
        On Android 12 the ``-d`` flag is silently ignored and input goes
        to display 0 anyway — this is documented and handled gracefully.
        """
        cmd = ['-s', self.device, 'shell', 'input']
        if display_id is not None:
            cmd += ['-d', str(display_id)]
        return cmd + args

    def disconnect(self):
        """Disconnect from device."""
        self._run(['disconnect', self.device])
        self.connected = False

    def _raw_screencap(self):
        """Grab raw bytes from ADB screencap.

        MuMu 12 default ``screencap -p`` already returns the game display
        (Display #4) in landscape orientation — fresh, not cached.
        Do NOT use ``-d 0`` which captures the launcher display instead.
        """
        if not self._ensure_connected():
            return None
        stdout, _, code = self._run(['-s', self.device, 'exec-out', 'screencap', '-p'])
        if code != 0:
            return None
        return stdout

    def get_vlm_ready_screenshot(self):
        """Capture a landscape-oriented screenshot for VLM (MiMo) consumption.

        Returns a 1920×1080 BGR numpy array — the 'upright' game view
        that multimodal models (MiMo-v2.5-Pro, GPT-4V, etc.) recognise
        with highest accuracy.

        MuMu 12 default screencap already returns the game display in
        landscape (1920×1080), so no rotation is needed.

        Coordinate contract
        -------------------
        The returned image lives in *game-space* (1920 wide × 1080 tall).
        VLM grounding outputs are expected in this same space and will be
        forwarded to ``tap_from_vlm_coordinate()`` for ADB execution.
        """
        raw = self._raw_screencap()
        if raw is None:
            if self._last_screenshot is not None:
                return self._last_screenshot
            raise RuntimeError('Not connected and no cached screenshot')

        buf = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError('Failed to decode screenshot')

        h, w = img.shape[:2]
        # MuMu 12 default screencap returns landscape (w > h) — already correct.
        # If somehow we get portrait (h > w), rotate 90° CW as safety fallback.
        if h > w:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        self._last_screenshot = img
        return img

    def screenshot(self):
        """Capture screenshot as BGR numpy array for internal template matching.

        Same pipeline as ``get_vlm_ready_screenshot``; kept as alias for
        backward compatibility with tasks/image_rec code.
        """
        return self.get_vlm_ready_screenshot()

    def tap_from_vlm_coordinate(self, x_model, y_model, model_res=(1920, 1080)):
        """Convert VLM normalised / game-space coordinates to ADB tap.

        Parameters
        ----------
        x_model, y_model : float or int
            Coordinates in the VLM's output space (typically 0-1000
            normalised, or direct pixel coords in 1920×1080 game space).
            If normalised (0-1000), multiply by ``model_res`` first.
        model_res : tuple[int, int]
            Width × height of the coordinate space the model returns.

        The mapping from game-space (landscape 1920×1080) to ADB physical
        portrait (1080×1920) is the 90° CW rotation inverse::

            x_adb = y_game
            y_adb = 1920 - x_game
        """
        # Clamp to valid range
        x_game = max(0, min(model_res[0], float(x_model)))
        y_game = max(0, min(model_res[1], float(y_model)))

        # Inverse of 90° CW rotation
        x_adb = int(y_game)
        y_adb = int(self._phys_h - x_game)

        self.tap(x_adb, y_adb, portrait_coords=True)
        logger.debug(f'VLM tap: model({x_model},{y_model}) -> game({x_game},{y_game}) -> adb({x_adb},{y_adb})')

    def tap(self, x, y, duration=None, portrait_coords=False):
        """Tap at coordinates.

        Args:
            x, y: Coordinates to tap.
                  portrait_coords=False (default): landscape game coords (1920x1080),
                      internally converted to ADB portrait coords.
                  portrait_coords=True: already in ADB portrait coords (1080x1920),
                      sent directly.
        """
        if not self._ensure_connected():
            return
        if portrait_coords:
            px, py = max(0, min(self._phys_w, int(x))), max(0, min(self._phys_h, int(y)))
        else:
            px, py = self._game_to_portrait(x, y)
        did = self._game_display if self._game_display else None
        if duration:
            self._run(self._input_cmd(['swipe',
                       str(px), str(py), str(px), str(py), str(duration)], display_id=did))
        else:
            self._run(self._input_cmd(['tap', str(px), str(py)], display_id=did))
        logger.debug(f'Tap: ({x},{y}) {"portrait" if portrait_coords else "game"} -> adb({px},{py}) d{did}')

    def swipe(self, x1, y1, x2, y2, duration=300):
        """Swipe from (x1,y1) to (x2,y2) in landscape coordinates."""
        px1, py1 = self._game_to_portrait(x1, y1)
        px2, py2 = self._game_to_portrait(x2, y2)
        did = self._game_display if self._game_display else None
        self._run(self._input_cmd(['swipe',
                   str(px1), str(py1), str(px2), str(py2), str(duration)], display_id=did))

    def long_press(self, x, y, duration=1000):
        """Long press at coordinates."""
        self.tap(x, y, duration=duration)

    def key_event(self, keycode):
        """Send a key event to the game display."""
        did = self._game_display if self._game_display else None
        self._run(self._input_cmd(['keyevent', str(keycode)], display_id=did))

    def press_back(self):
        """Press back button."""
        self.key_event(4)

    def press_home(self):
        """Press home button."""
        self.key_event(3)

    def get_screen_size(self):
        """Get device screen resolution."""
        stdout, _, _ = self._run(['-s', self.device, 'shell', 'wm', 'size'])
        # Output like "Physical size: 1280x720"
        parts = stdout.decode().strip().split(':')[-1].strip().split('x')
        return int(parts[0]), int(parts[1])

    def install_apk(self, apk_path):
        """Install APK on device."""
        stdout, stderr, code = self._run(['-s', self.device, 'install', '-r', apk_path])
        return code == 0

    def is_connected(self):
        """Check if device is still connected."""
        try:
            stdout, _, code = self._run(['-s', self.device, 'get-state'], timeout=5)
            return stdout.decode().strip() == 'device'
        except Exception:
            return False

    def shell(self, command):
        """Execute a shell command on device."""
        stdout, stderr, code = self._run(['-s', self.device, 'shell', command])
        return stdout.decode()
