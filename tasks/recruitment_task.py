"""Auto recruitment task."""
import time
import logging
from .base_task import BaseTask

logger = logging.getLogger(__name__)

# Arknights recruitment tag combinations (simplified)
TAG_COMBINATIONS = {
    ('先锋', '费用回复'): ['德克萨斯', '凛冬'],
    ('近卫', '输出'): ['银灰', '陈', '拉普兰德'],
    ('术师', '群攻'): ['伊芙利特', '天火'],
    ('治疗', '支援'): ['白面鸮', '赫默'],
    ('重装', '防护'): ['星熊', '蛇屠箱'],
    ('狙击', '减速'): ['白雪', '流星'],
    ('辅助', '削弱'): ['初雪', '地灵'],
    ('特种', '位移'): ['崖心', '暗索'],
}


class RecruitmentTask(BaseTask):
    """Automates recruitment: tag selection, time setting, confirmation."""

    @property
    def task_name(self):
        return 'Auto Recruitment'

    def execute(self):
        cfg = self.config.get('tasks', {}).get('recruitment', {})
        preferred = cfg.get('preferred_tags', [])
        auto_confirm = cfg.get('auto_confirm', True)

        self.log('info', 'Starting recruitment...')

        if not self._navigate_to_recruitment():
            self.log('error', 'Failed to navigate to recruitment')
            return False

        # Find available recruitment slots
        slots = self._find_available_slots()
        if not slots:
            self.log('info', 'No available recruitment slots')
            return True

        self.log('info', f'Found {len(slots)} available slot(s)')

        for slot_pos in slots:
            if not self.should_continue():
                break
            self._process_recruitment_slot(slot_pos, preferred, auto_confirm)

        self.log('info', 'Recruitment completed')
        return True

    def _navigate_to_recruitment(self):
        """Navigate to recruitment screen."""
        for _ in range(3):
            if not self.should_continue():
                return False
            if self.tap_template('nav_recruit', threshold=0.7):
                self._interruptible_sleep(2)
                return True
            # Try from main menu -> HR
            if self.tap_template('nav_hr', threshold=0.7):
                self._interruptible_sleep(2)
                return True
        return False

    def _find_available_slots(self):
        """Find available recruitment slots."""
        screen = self.adb.screenshot()
        slots = self.img_rec.find_all_templates(screen, 'recruit_slot_empty', threshold=0.7)
        return slots

    def _process_recruitment_slot(self, slot_pos, preferred_tags, auto_confirm):
        """Process a single recruitment slot."""
        # Tap the slot
        self.tap_and_wait(slot_pos[0], slot_pos[1], 1.5)

        # Read available tags
        tags = self._read_recruitment_tags()
        self.log('info', f'Available tags: {tags}')

        # Select best tags
        selected = self._select_best_tags(tags, preferred_tags)
        if selected:
            self.log('info', f'Selected tags: {selected}')
        else:
            self.log('info', 'No optimal tags found, selecting 3:50 timer')
            # Select timer for 3:50 to guarantee 3-star
            self._set_timer(3, 50)

        if auto_confirm:
            self.wait_and_tap('recruit_confirm', timeout=5)
            self._interruptible_sleep(1)

    def _read_recruitment_tags(self):
        """Read available recruitment tags from screen."""
        # This would use OCR in a real implementation
        # For now, check each known tag position
        tags = []
        tag_positions = [
            (300, 250), (450, 250), (600, 250),
            (375, 320), (525, 320)
        ]
        screen = self.adb.screenshot()
        known_tags = ['先锋', '近卫', '重装', '狙击', '术师', '治疗', '辅助', '特种',
                      '输出', '生存', '群攻', '减速', '支援', '快速复活', '费用回复',
                      '控场', '位移', '爆发', '削弱', '防护', '治疗']
        for tag in known_tags:
            if self.img_rec.find_template(screen, f'tag_{tag}', threshold=0.8):
                tags.append(tag)
        return tags

    def _select_best_tags(self, available_tags, preferred):
        """Select optimal tag combination for high-rarity operators."""
        # Check 4-star+ combinations
        best_combo = None
        best_score = 0

        # Simple scoring: prefer tags that match known good combinations
        for combo, operators in TAG_COMBINATIONS.items():
            if all(t in available_tags for t in combo):
                score = len(operators) * 2
                if any(t in preferred for t in combo):
                    score += 5
                if score > best_score:
                    best_score = score
                    best_combo = combo

        if best_combo:
            screen = self.adb.screenshot()
            for tag in best_combo:
                result = self.img_rec.find_template(screen, f'tag_{tag}', threshold=0.8)
                if result:
                    self.tap_and_wait(result[0], result[1], 0.5)
            # Set timer to 9:00 for maximum rarity
            self._set_timer(9, 0)
            return list(best_combo)
        return None

    def _set_timer(self, hours, minutes):
        """Set recruitment timer."""
        # Tap timer adjustment buttons
        # Hour up/down buttons and minute up/down buttons
        for _ in range(hours):
            self.tap_template('timer_hour_up', threshold=0.8)
            self._interruptible_sleep(0.2)
        for _ in range(minutes // 10):
            self.tap_template('timer_min_up', threshold=0.8)
            self._interruptible_sleep(0.2)
