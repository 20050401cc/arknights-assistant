"""Base/infrastructure management task."""
import time
import logging
from .base_task import BaseTask
from core.game_state import GameState

logger = logging.getLogger(__name__)


class BaseManagementTask(BaseTask):
    """Automates base operations: shift changes, resource collection, clue exchange."""

    @property
    def task_name(self):
        return 'Base Management'

    def execute(self):
        cfg = self.config.get('tasks', {}).get('base', {})
        self.log('info', 'Starting base management...')

        if not self._navigate_to_base():
            self.log('error', 'Failed to navigate to base')
            return False

        success = True
        if cfg.get('auto_collect', True):
            self._collect_resources()

        if cfg.get('auto_shift', True):
            self._auto_shift_operators()

        if cfg.get('auto_clue', True):
            self._manage_clues()

        self.log('info', 'Base management completed')
        return success

    def _navigate_to_base(self):
        """Navigate to the base overview."""
        # Try tapping base navigation button from main menu
        for _ in range(3):
            if not self.should_continue():
                return False
            if self.tap_template('nav_base', threshold=0.7):
                self._interruptible_sleep(3)
                # Verify we're in base
                screen = self.adb.screenshot()
                if self.game.detect_state(screen) == GameState.BASE_OVERVIEW:
                    return True
            self.tap_and_wait(640, 650, 1.5)
        return False

    def _collect_resources(self):
        """Collect resources from trading post, factory, etc."""
        self.log('info', 'Collecting base resources...')
        # Tap on notification icons to collect
        screen = self.adb.screenshot()
        # Look for resource collection indicators
        notifications = self.img_rec.find_all_templates(screen, 'base_collect', threshold=0.7)
        for x, y, conf in notifications:
            if not self.should_continue():
                return
            self.tap_and_wait(x, y, 1.0)
        self._interruptible_sleep(1)

    def _auto_shift_operators(self):
        """Automatically swap exhausted operators."""
        self.log('info', 'Auto-shifting operators...')
        # This is the most complex part - needs to:
        # 1. Enter each room
        # 2. Check operator morale
        # 3. Replace exhausted operators
        # Simplified: tap through dormitories and facilities
        rooms = ['trading_post', 'factory', 'control_station', 'dormitory']
        for room in rooms:
            if not self.should_continue():
                return
            if self.tap_template(f'base_{room}', threshold=0.6):
                self._interruptible_sleep(2)
                self._check_and_replace_operators()
                # Go back to base overview
                self.adb.press_back()
                self._interruptible_sleep(1.5)

    def _check_and_replace_operators(self):
        """Check current room operators and replace if needed."""
        # Look for exhausted operator indicators (red morale bar)
        screen = self.adb.screenshot()
        exhausted = self.img_rec.find_template(screen, 'operator_exhausted', threshold=0.7)
        if exhausted:
            self.log('info', 'Found exhausted operator, replacing...')
            # Tap the operator slot
            self.tap_and_wait(exhausted[0], exhausted[1], 1.0)
            # Tap confirm/swap
            self.wait_and_tap('confirm_swap', timeout=5)

    def _manage_clues(self):
        """Manage clue exchange in reception room."""
        self.log('info', 'Managing clues...')
        # Enter reception room
        if self.tap_template('base_reception', threshold=0.6):
            self._interruptible_sleep(2)
            # Check for clue exchange button
            if self.tap_template('clue_exchange', threshold=0.7):
                self._interruptible_sleep(1)
                # Confirm exchange
                self.wait_and_tap('confirm_b', timeout=5)
            self.adb.press_back()
            self._interruptible_sleep(1)
