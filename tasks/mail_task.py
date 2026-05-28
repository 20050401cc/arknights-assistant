"""Mail collection task."""
import time
import logging
from .base_task import BaseTask

logger = logging.getLogger(__name__)


class MailTask(BaseTask):
    """Collects mail and attachments."""

    @property
    def task_name(self):
        return 'Mail Collection'

    def execute(self):
        self.log('info', 'Checking mail...')

        if not self._open_mail():
            self.log('warning', 'Could not open mail')
            return False

        collected = self._collect_all_mail()
        self.log('info', f'Collected {collected} mail(s)')

        # Return to main menu
        self.adb.press_back()
        self._interruptible_sleep(1)
        return True

    def _open_mail(self):
        """Open the mail interface."""
        for _ in range(3):
            if not self.should_continue():
                return False
            if self.tap_template('mail_icon', threshold=0.7):
                self._interruptible_sleep(2)
                return True
            # Fallback: tap top-right area where mail icon usually is
            self.tap_and_wait(1200, 50, 1.0)
        return False

    def _collect_all_mail(self):
        """Tap collect all button or collect individual mails."""
        collected = 0

        # Try "collect all" button first
        if self.tap_template('mail_collect_all', threshold=0.8):
            self._interruptible_sleep(2)
            # Confirm collection
            self.wait_and_tap('confirm_b', timeout=5)
            return -1  # Unknown count but collected

        # Collect individual mails
        for _ in range(20):
            if not self.should_continue():
                break
            screen = self.adb.screenshot()
            mail = self.img_rec.find_template(screen, 'mail_item', threshold=0.7)
            if not mail:
                break
            self.tap_and_wait(mail[0], mail[1], 1.0)
            # Tap collect button
            if self.wait_and_tap('mail_collect_btn', timeout=3):
                collected += 1
                self._interruptible_sleep(1)
                # Close mail detail
                self.adb.press_back()
                self._interruptible_sleep(0.5)
            else:
                self.adb.press_back()
                self._interruptible_sleep(0.5)
                break
        return collected
