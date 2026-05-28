"""Base task class for all automation tasks."""
import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class BaseTask(QThread):
    """Base class for all game automation tasks."""

    # Signals for UI communication
    log_signal = pyqtSignal(str, str)        # (level, message)
    progress_signal = pyqtSignal(int, int)    # (current, total)
    status_signal = pyqtSignal(str)           # status message
    finished_signal = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, adb, img_rec, game_analyzer, config):
        super().__init__()
        self.adb = adb
        self.img_rec = img_rec
        self.game = game_analyzer
        self.config = config
        self._running = False
        self._paused = False
        self._action_memory = getattr(game_analyzer, 'action_memory', None)

    @property
    def task_name(self):
        return 'BaseTask'

    def run(self):
        """Main task execution loop. Override in subclasses."""
        self._running = True
        self.log('info', f'{self.task_name} started')
        try:
            success = self.execute()
            self.finished_signal.emit(success, 'Task completed' if success else 'Task failed')
        except Exception as e:
            self.log('error', f'{self.task_name} error: {e}')
            self.finished_signal.emit(False, str(e))
        finally:
            self._running = False

    def execute(self):
        """Override this method with task logic. Return True on success."""
        raise NotImplementedError

    def stop(self):
        """Request task to stop."""
        self._running = False

    def pause(self):
        """Toggle pause."""
        self._paused = not self._paused

    def wait_if_paused(self):
        """Block if task is paused. Also checks for stop/interrupt."""
        while self._paused and self._running and not self.isInterruptionRequested():
            time.sleep(0.1)

    def should_continue(self):
        """Check if task should keep running."""
        return self._running and not self.isInterruptionRequested()

    def _interruptible_sleep(self, seconds):
        """Sleep in small chunks so stop/pause can interrupt."""
        end = time.time() + seconds
        while time.time() < end and self.should_continue() and not self._paused:
            time.sleep(min(0.2, end - time.time()))

    def log(self, level, message):
        """Emit a log message to UI."""
        self.log_signal.emit(level, f'[{self.task_name}] {message}')
        getattr(logger, level)(message)

    def tap_and_wait(self, x, y, wait=1.0):
        """Tap a position and wait (interruptible)."""
        self.adb.tap(x, y)
        self._interruptible_sleep(wait)

    def tap_template(self, template_name, timeout=10, threshold=0.8):
        """Find and tap a template on screen. Returns True if found.

        CTM: 记录操作历史，检测卡住模式。
        """
        # CTM: 检查是否应该跳过（历史连续失败）
        if self._action_memory and self._action_memory.should_skip_action(
            self.game._prev_state.value, "tap_template", template_name
        ):
            self.log('warning', f'CTM: 跳过重复失败动作 tap_template:{template_name}')
            return False

        screen = self.adb.screenshot()
        state = self.game._prev_state.value
        result = self.img_rec.find_template(screen, template_name, threshold)
        if result:
            self.adb.tap(result[0], result[1])
            self._interruptible_sleep(0.5)
            if self._action_memory:
                self._action_memory.record(state, "tap_template", template_name, "success")
            return True
        if self._action_memory:
            self._action_memory.record(state, "tap_template", template_name, "fail")
        return False

    def wait_and_tap(self, template_name, timeout=15, threshold=0.8):
        """Wait for a template to appear, then tap it."""
        result = self.img_rec.wait_for_template(
            self.adb.screenshot, template_name, timeout, threshold
        )
        if result:
            self.adb.tap(result[0], result[1])
            self._interruptible_sleep(0.5)
            return True
        self.log('warning', f'Timeout waiting for: {template_name}')
        return False

    def wait_for_state(self, target_state, timeout=30, interval=1.0):
        """Wait until game reaches target state."""
        start = time.time()
        while time.time() - start < timeout:
            if not self.should_continue():
                return False
            screen = self.adb.screenshot()
            state = self.game.detect_state(screen)
            if state == target_state:
                return True
            self._interruptible_sleep(interval)
        return False

    def safe_tap(self, template_name, retries=3, delay=1.0):
        """Try to tap a template multiple times with retries.

        CTM: 检测卡住时提前终止，不再盲目重试。
        """
        for i in range(retries):
            if not self.should_continue():
                return False
            # CTM: 检测卡住，提前终止
            if self._action_memory and self._action_memory.is_stuck(self.game._prev_state.value):
                suggestion = self._action_memory.suggest_action(self.game._prev_state.value)
                if suggestion:
                    self.log('warning', f'CTM: {suggestion["reason"]}')
                    # 如果有建议动作，执行它
                    if suggestion.get('action_type') == 'key_event':
                        self.adb.key_event(int(suggestion['action_detail']))
                        self._interruptible_sleep(1)
                        return False
            if self.tap_template(template_name):
                return True
            self._interruptible_sleep(delay)
        return False
