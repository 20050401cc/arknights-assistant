"""Auto combat/farming task."""
import time
import logging
from .base_task import BaseTask
from core.game_state import GameState

logger = logging.getLogger(__name__)


class CombatTask(BaseTask):
    """Automates combat: stage selection, battle, result collection."""

    @property
    def task_name(self):
        return 'Auto Combat'

    def execute(self):
        cfg = self.config.get('tasks', {}).get('combat', {})
        stage = cfg.get('stage', 'CE-6')
        max_times = cfg.get('times', 99)
        use_potion = cfg.get('use_sanity_potion', False)
        use_originium = cfg.get('use_originium', False)

        completed = 0
        self.log('info', f'Starting combat: {stage} x{max_times}')

        for i in range(max_times):
            if not self.should_continue():
                break
            self.wait_if_paused()

            self.log('info', f'Battle {i+1}/{max_times}')
            self.status_signal.emit(f'Battle {i+1}/{max_times}')
            self.progress_signal.emit(i, max_times)

            success = self._do_one_battle(use_potion, use_originium)
            if not success:
                self.log('warning', f'Battle {i+1} failed or stuck')
                break
            completed += 1
            self._interruptible_sleep(1)

        self.log('info', f'Combat finished: {completed}/{max_times} completed')
        return completed > 0

    def _do_one_battle(self, use_potion, use_originium):
        """Execute one full battle cycle."""
        # Step 1: Ensure we're on combat preparation screen
        screen = self.adb.screenshot()
        state = self.game.detect_state(screen)

        if state != GameState.COMBAT_PREPARE:
            # Try to navigate to combat
            if not self._navigate_to_combat():
                return False

        # Step 2: Check sanity
        if not self.game.is_sanity_enough(screen):
            if use_potion:
                self.log('info', 'Using sanity potion...')
                if not self._use_sanity_recovery('potion'):
                    self.log('warning', 'No potions available')
                    return False
            elif use_originium:
                self.log('info', 'Using originium...')
                if not self._use_sanity_recovery('originium'):
                    return False
            else:
                self.log('info', 'Insanity insufficient, waiting...')
                return self._wait_for_sanity()

        # Step 3: Start battle
        self.log('info', 'Starting battle...')
        if not self.wait_and_tap('combat_start_b', timeout=5):
            # Fallback: tap the start button area directly
            self.tap_and_wait(1100, 650, 1.0)

        # Step 4: Wait for battle to finish (auto-deploy mode)
        self.log('info', 'Battle in progress...')
        self._interruptible_sleep(3)

        # Wait for result screen
        if not self._wait_for_battle_end(timeout=300):
            self.log('warning', 'Battle timed out')
            return False

        # Step 5: Collect result
        return self._collect_result()

    def _navigate_to_combat(self):
        """Navigate from main menu to combat screen."""
        # Tap the combat button on main menu
        for _ in range(3):
            if not self.should_continue():
                return False
            if self.tap_template('nav_combat', threshold=0.7):
                self._interruptible_sleep(2)
                return True
            # Fallback: tap bottom-left area where combat button usually is
            self.tap_and_wait(200, 650, 1.5)
        return False

    def _wait_for_battle_end(self, timeout=300):
        """Wait for battle to complete."""
        start = time.time()
        while time.time() - start < timeout:
            if not self.should_continue():
                return False
            screen = self.adb.screenshot()
            state = self.game.detect_state(screen)
            if state in (GameState.COMBAT_RESULT, GameState.COMBAT_FAILED):
                return True
            self._interruptible_sleep(2)
        return False

    def _collect_result(self):
        """Tap through result screens to collect rewards."""
        self.log('info', 'Collecting rewards...')
        # Tap through result screens (usually multiple taps needed)
        for _ in range(5):
            if not self.should_continue():
                return False
            self._interruptible_sleep(1.5)
            screen = self.adb.screenshot()
            # Tap center of screen to advance
            self.adb.tap(640, 360)
        self._interruptible_sleep(1)
        return True

    def _use_sanity_recovery(self, method='potion'):
        """Use sanity potion or originium."""
        # Find and tap the recovery button
        if self.tap_template('sanity_recover'):
            self._interruptible_sleep(1)
            if method == 'potion':
                return self.tap_template('use_potion')
            else:
                return self.tap_template('use_originium')
        return False

    def _wait_for_sanity(self, max_wait=3600):
        """Wait for sanity to regenerate."""
        self.log('info', 'Waiting for sanity regeneration...')
        start = time.time()
        while time.time() - start < max_wait:
            if not self.should_continue():
                return False
            screen = self.adb.screenshot()
            if self.game.is_sanity_enough(screen):
                self.log('info', 'Sanity recovered!')
                return True
            remaining = int(max_wait - (time.time() - start))
            self.status_signal.emit(f'等待理智恢复... ({remaining}s)')
            self._interruptible_sleep(30)
        return False
