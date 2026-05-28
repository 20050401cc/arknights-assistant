"""CTM Action Memory — 操作时间历史记忆

借鉴 CTM 的"神经元时间历史"概念：
- 每个操作记录时间戳、游戏状态、动作、结果
- 检测重复失败模式，避免盲目重试
- 识别"卡住"状态，自动切换策略
- 提供基于历史成功率的动作建议
"""
import time
import json
import os
import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "action_history.json")
MAX_HISTORY = 500  # 内存中保留的最大记录数
STUCK_THRESHOLD = 5  # 同一状态连续出现 N 次视为"卡住"
FAIL_PATTERN_THRESHOLD = 3  # 同一动作在同一状态下失败 N 次视为模式


@dataclass
class ActionRecord:
    """单条操作记录"""
    timestamp: float
    game_state: str          # 操作时的游戏状态
    action_type: str         # tap / swipe / wait / key_event
    action_detail: str       # 坐标、按键等具体信息
    result: str              # success / fail / timeout / unknown
    new_state: str = ""      # 操作后的游戏状态
    duration: float = 0.0    # 操作耗时(秒)
    error: str = ""          # 错误信息


class ActionMemory:
    """操作历史记忆系统

    CTM 核心机制映射：
    - 时间历史：记录每个操作的状态-动作-结果序列
    - 模式识别：检测重复失败，触发策略切换
    - 同步感知：识别多个任务间的冲突模式
    """

    def __init__(self, memory_file: str = None):
        self._history: deque[ActionRecord] = deque(maxlen=MAX_HISTORY)
        self._memory_file = memory_file or MEMORY_FILE
        self._state_durations: dict[str, list[float]] = {}  # 状态停留时间
        self._fail_counts: dict[str, int] = {}  # (state, action) -> 连续失败次数
        self._load()

    def _load(self):
        """从磁盘加载历史记录"""
        if not os.path.exists(self._memory_file):
            return
        try:
            with open(self._memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("history", [])[-MAX_HISTORY:]:
                self._history.append(ActionRecord(**item))
            logger.info(f"Loaded {len(self._history)} action records from disk")
        except Exception as e:
            logger.warning(f"Failed to load action history: {e}")

    def save(self):
        """持久化历史记录到磁盘"""
        try:
            os.makedirs(os.path.dirname(self._memory_file), exist_ok=True)
            data = {
                "history": [asdict(r) for r in self._history],
                "saved_at": time.time(),
            }
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save action history: {e}")

    # ── 记录操作 ──

    def record(self, game_state: str, action_type: str, action_detail: str,
               result: str, new_state: str = "", duration: float = 0.0, error: str = ""):
        """记录一次操作"""
        rec = ActionRecord(
            timestamp=time.time(),
            game_state=game_state,
            action_type=action_type,
            action_detail=action_detail,
            result=result,
            new_state=new_state,
            duration=duration,
            error=error,
        )
        self._history.append(rec)

        # 更新失败计数
        key = f"{game_state}:{action_type}:{action_detail}"
        if result == "fail":
            self._fail_counts[key] = self._fail_counts.get(key, 0) + 1
        elif result == "success":
            self._fail_counts.pop(key, None)

        # 定期持久化
        if len(self._history) % 50 == 0:
            self.save()

    # ── CTM 核心：模式检测 ──

    def is_stuck(self, current_state: str) -> bool:
        """检测是否卡在同一状态（CTM: 时间历史中的同步停滞）"""
        if len(self._history) < STUCK_THRESHOLD:
            return False
        recent = list(self._history)[-STUCK_THRESHOLD:]
        return all(r.game_state == current_state for r in recent)

    def get_stuck_actions(self, current_state: str) -> list[str]:
        """获取卡住期间尝试过的所有动作"""
        stuck_actions = []
        for r in reversed(self._history):
            if r.game_state != current_state:
                break
            stuck_actions.append(f"{r.action_type}:{r.action_detail}")
        return list(set(stuck_actions))

    def should_skip_action(self, game_state: str, action_type: str, action_detail: str) -> bool:
        """判断是否应该跳过这个动作（连续失败过多）"""
        key = f"{game_state}:{action_type}:{action_detail}"
        fails = self._fail_counts.get(key, 0)
        if fails >= FAIL_PATTERN_THRESHOLD:
            logger.warning(f"CTM: 跳过重复失败动作 ({fails}次): {key}")
            return True
        return False

    def get_success_rate(self, game_state: str, action_type: str) -> float:
        """获取某状态下某类动作的历史成功率"""
        total, success = 0, 0
        for r in self._history:
            if r.game_state == game_state and r.action_type == action_type:
                total += 1
                if r.result == "success":
                    success += 1
        return success / total if total > 0 else 0.5

    # ── CTM 核心：自适应建议 ──

    def suggest_action(self, game_state: str) -> Optional[dict]:
        """基于历史给出建议（CTM: 同步即表征 — 从历史模式中提取最优动作）"""
        if not self.is_stuck(game_state):
            return None  # 没卡住，不需要建议

        # 找出在该状态下成功过的动作
        successful_actions = {}
        for r in self._history:
            if r.game_state == game_state and r.result == "success":
                key = f"{r.action_type}:{r.action_detail}"
                successful_actions[key] = successful_actions.get(key, 0) + 1

        # 排除当前卡住期间已经尝试过的动作
        stuck_actions = self.get_stuck_actions(game_state)
        for tried in stuck_actions:
            successful_actions.pop(tried, None)

        if successful_actions:
            best = max(successful_actions, key=successful_actions.get)
            action_type, detail = best.split(":", 1)
            return {
                "action_type": action_type,
                "action_detail": detail,
                "confidence": successful_actions[best],
                "reason": f"CTM: 卡在 {game_state}，历史最优动作: {best} (成功{successful_actions[best]}次)"
            }

        # 没有成功历史，建议按 back 重置
        return {
            "action_type": "key_event",
            "action_detail": "4",  # KEYCODE_BACK
            "confidence": 1,
            "reason": f"CTM: 卡在 {game_state}，无成功历史，建议返回重置"
        }

    # ── 统计 ──

    def get_stats(self) -> dict:
        """获取历史统计摘要"""
        if not self._history:
            return {"total": 0}

        total = len(self._history)
        success = sum(1 for r in self._history if r.result == "success")
        fail = sum(1 for r in self._history if r.result == "fail")

        state_counts = {}
        for r in self._history:
            state_counts[r.game_state] = state_counts.get(r.game_state, 0) + 1

        return {
            "total": total,
            "success": success,
            "fail": fail,
            "success_rate": f"{success/total*100:.1f}%",
            "top_states": sorted(state_counts.items(), key=lambda x: -x[1])[:5],
            "current_fail_patterns": len(self._fail_counts),
        }

    def reset(self):
        """清空历史"""
        self._history.clear()
        self._fail_counts.clear()
        self._state_durations.clear()
        if os.path.exists(self._memory_file):
            os.remove(self._memory_file)
        logger.info("Action memory reset")
