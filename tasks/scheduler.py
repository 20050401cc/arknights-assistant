"""任务调度器 - 按顺序或循环执行任务队列"""
import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TaskScheduler(QThread):
    """按顺序运行多个任务的调度器。"""

    log_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)
    task_started = pyqtSignal(str)
    task_finished = pyqtSignal(str, bool)

    def __init__(self, config, action_memory=None):
        super().__init__()
        self.config = config
        self._running = False
        self._paused = False
        self._task_queue = []
        self._loop_enabled = False
        self._loop_interval = 300
        self._action_memory = action_memory  # CTM: 操作记忆

    def add_task(self, task):
        self._task_queue.append(task)

    def clear_tasks(self):
        self._task_queue.clear()

    def set_loop(self, enabled, interval=300):
        self._loop_enabled = enabled
        self._loop_interval = interval

    def run(self):
        self._running = True
        self.log('info', '调度器已启动')

        while self._running and not self.isInterruptionRequested():
            for task in self._task_queue:
                if not self._running or self.isInterruptionRequested():
                    break
                self._wait_if_paused()

                self.log('info', f'开始任务: {task.task_name}')
                self.task_started.emit(task.task_name)

                task.start()
                # 等待任务完成，同时检查中断信号
                while task.isRunning():
                    if not self._running or self.isInterruptionRequested():
                        task.requestInterruption()
                        task._running = False
                        task._paused = False
                        task.wait(2000)
                        if task.isRunning():
                            task.terminate()
                            task.wait(1000)
                        break
                    self._wait_if_paused()
                    time.sleep(0.2)

                self.task_finished.emit(task.task_name, True)

            if not self._loop_enabled or not self._running:
                break

            self.log('info', f'循环模式: 等待 {self._loop_interval} 秒...')
            self.status_signal.emit(f'等待 {_format_time(self._loop_interval)}')

            wait_start = time.time()
            while time.time() - wait_start < self._loop_interval:
                if not self._running or self.isInterruptionRequested():
                    break
                self._wait_if_paused()
                remaining = int(self._loop_interval - (time.time() - wait_start))
                self.status_signal.emit(f'下次运行: {_format_time(remaining)}')
                time.sleep(1)

        self._running = False
        if self._action_memory:
            self._action_memory.save()
            stats = self._action_memory.get_stats()
            self.log('info', f'调度器已停止 | CTM记忆: {stats}')
        else:
            self.log('info', '调度器已停止')

    def stop(self):
        """停止调度器和所有正在运行的任务。"""
        self._running = False
        self._paused = False   # 解除暂停，让 wait_if_paused 放行
        self.requestInterruption()
        for task in self._task_queue:
            if task.isRunning():
                task.requestInterruption()
                task._running = False
                task._paused = False
                task.wait(3000)
                if task.isRunning():
                    task.terminate()
                    task.wait(1000)

    def pause(self):
        """切换暂停/继续。"""
        self._paused = not self._paused
        for task in self._task_queue:
            if task.isRunning():
                task._paused = self._paused

    def is_paused(self):
        return self._paused

    def _wait_if_paused(self):
        while self._paused and self._running and not self.isInterruptionRequested():
            time.sleep(0.1)

    def log(self, level, message):
        self.log_signal.emit(level, f'[调度] {message}')
        getattr(logger, level)(message)


def _format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f'{h:02d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'
