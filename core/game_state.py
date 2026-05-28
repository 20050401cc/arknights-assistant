"""Game state detection for Arknights."""
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class GameState(Enum):
    UNKNOWN = 'unknown'
    MAIN_MENU = 'main_menu'
    COMBAT_SELECT = 'combat_select'
    COMBAT_PREPARE = 'combat_prepare'
    COMBAT_IN_PROGRESS = 'combat_in_progress'
    COMBAT_RESULT = 'combat_result'
    COMBAT_FAILED = 'combat_failed'
    BASE_OVERVIEW = 'base_overview'
    BASE_ROOM = 'base_room'
    RECRUITMENT = 'recruitment'
    RECRUITMENT_RESULT = 'recruitment_result'
    SHOP = 'shop'
    MAIL = 'mail'
    NETWORK_ERROR = 'network_error'
    LOGIN_SCREEN = 'login_screen'
    ANNOUNCEMENT = 'announcement'


class GameAnalyzer:
    """Analyzes game screen to determine current state.

    CTM: 集成 ActionMemory，在状态检测时同步检查历史模式。
    """

    def __init__(self, img_rec, action_memory=None):
        self.img_rec = img_rec
        self.action_memory = action_memory  # CTM 时间历史
        self._prev_state = GameState.UNKNOWN
        self._state_enter_time = 0

    def detect_state(self, screen):
        """Detect current game state from screenshot.

        CTM: 记录状态转换，检测卡住模式。
        """
        import time
        checks = [
            ('ann_c', GameState.ANNOUNCEMENT),
            ('login_start_b', GameState.LOGIN_SCREEN),
            ('nav_home', GameState.MAIN_MENU),
            ('combat_start_b', GameState.COMBAT_PREPARE),
            ('combat_auto', GameState.COMBAT_IN_PROGRESS),
            ('combat_result_s', GameState.COMBAT_RESULT),
            ('combat_failed_s', GameState.COMBAT_FAILED),
            ('base_dorm', GameState.BASE_OVERVIEW),
            ('recruit_b', GameState.RECRUITMENT),
            ('net_error', GameState.NETWORK_ERROR),
        ]
        detected = GameState.UNKNOWN
        for template_name, state in checks:
            result = self.img_rec.find_template(screen, template_name, threshold=0.75)
            if result:
                detected = state
                break

        # CTM: 状态转换追踪
        if detected != self._prev_state:
            logger.debug(f'State: {self._prev_state.value} -> {detected.value}')
            self._prev_state = detected
            self._state_enter_time = time.time()

        return detected

    def is_stuck(self) -> bool:
        """CTM: 检查当前是否卡住"""
        if self.action_memory:
            return self.action_memory.is_stuck(self._prev_state.value)
        return False

    def get_stuck_suggestion(self) -> dict | None:
        """CTM: 获取卡住时的建议动作"""
        if self.action_memory:
            return self.action_memory.suggest_action(self._prev_state.value)
        return None

    def get_sanity(self, screen):
        """Read current sanity value using template matching region."""
        # Crop the sanity region (top-right area of screen)
        # For 1280x720: sanity text is around (950, 20) to (1100, 60)
        sanity_region = self.img_rec.crop_region(screen, 930, 15, 1120, 65)
        # Use pixel analysis to detect sanity digits
        # This is a simplified heuristic - real implementation would use OCR
        return None  # Placeholder: actual OCR requires pytesseract

    def is_sanity_enough(self, screen, required=30):
        """Check if current sanity is enough for a battle."""
        sanity = self.get_sanity(screen)
        if sanity is None:
            return True  # Assume enough if can't detect
        return sanity >= required
