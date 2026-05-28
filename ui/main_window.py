"""明日方舟助手 - MuMu 模拟器版 主界面（v2 精致主题）"""
import json
import sys
import os
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QSpinBox, QGroupBox,
    QTextEdit, QProgressBar, QTabWidget, QFrame, QSlider, QLineEdit,
    QSplitter, QStatusBar, QToolBar, QSystemTrayIcon, QMenu, QApplication,
    QScrollArea, QMessageBox, QFileDialog, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QImage, QLinearGradient, QPainter

from core.adb_controller import ADBController
from core.image_recognition import ImageRecognition
from core.game_state import GameAnalyzer, GameState
from core.action_memory import ActionMemory
from core.mumu_detector import find_mumu_adb, connect_mumu, detect_mumu_instances
from tasks import CombatTask, BaseManagementTask, RecruitmentTask, MailTask, TaskScheduler

logger = logging.getLogger(__name__)

# ── 色彩常量 ────────────────────────────────────────────────────────────────
C_BG        = '#0f1923'   # 最深背景
C_SURFACE   = '#17212b'   # 卡片背景
C_SURFACE2  = '#1e2c3a'   # 输入框/次级面板
C_BORDER    = '#2b3d4f'   # 边框
C_ACCENT    = '#6cb4ee'   # 主题蓝
C_ACCENT2   = '#e07a5f'   # 强调橙红
C_GREEN     = '#66d9a0'   # 成功绿
C_YELLOW    = '#f0c674'   # 警告黄
C_RED       = '#f26d7e'   # 错误红
C_TEXT      = '#c5d0db'   # 正文
C_TEXT_DIM  = '#5f7385'   # 次要文字
C_WHITE     = '#e8edf2'   # 亮色文字


# ── 全局样式表 ───────────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
/* ─── 全局 ─── */
QMainWindow, QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {C_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C_BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C_ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ─── 分组卡片 ─── */
QGroupBox {{
    background-color: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    margin-top: 18px;
    padding: 18px 14px 14px 14px;
    font-weight: bold;
    font-size: 13px;
    color: {C_ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 2px;
    padding: 0 8px;
    color: {C_ACCENT};
    font-size: 13px;
}}

/* ─── 按钮 ─── */
QPushButton {{
    background-color: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    color: {C_TEXT};
    font-weight: 500;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: #253545;
    border-color: {C_ACCENT};
    color: {C_WHITE};
}}
QPushButton:pressed {{
    background-color: {C_ACCENT};
    color: {C_BG};
}}
QPushButton:disabled {{
    background-color: {C_SURFACE};
    color: {C_TEXT_DIM};
    border-color: {C_SURFACE};
}}
QPushButton#btn_start {{
    background-color: {C_ACCENT};
    border: none;
    color: {C_BG};
    font-size: 14px;
    font-weight: bold;
    padding: 10px 28px;
    border-radius: 8px;
}}
QPushButton#btn_start:hover {{
    background-color: #82c4f5;
}}
QPushButton#btn_start:pressed {{
    background-color: #4a9fd4;
}}
QPushButton#btn_stop {{
    background-color: {C_RED};
    border: none;
    color: white;
    font-weight: bold;
    border-radius: 8px;
}}
QPushButton#btn_stop:hover {{
    background-color: #f5899a;
}}
QPushButton#btn_pause {{
    border-radius: 8px;
}}

/* ─── 复选框 ─── */
QCheckBox {{
    spacing: 8px;
    color: {C_TEXT};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid {C_BORDER};
    background-color: {C_SURFACE2};
}}
QCheckBox::indicator:hover {{
    border-color: {C_ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
}}

/* ─── 输入控件 ─── */
QComboBox, QSpinBox, QLineEdit {{
    background-color: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    color: {C_WHITE};
    min-height: 18px;
    selection-background-color: {C_ACCENT};
    selection-color: {C_BG};
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{
    border-color: {C_ACCENT};
}}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
    border-color: {C_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {C_SURFACE};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_ACCENT};
    selection-color: {C_BG};
    color: {C_TEXT};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {C_SURFACE2};
    border: none;
    width: 18px;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

/* ─── 文本编辑器（日志） ─── */
QTextEdit {{
    background-color: {C_BG};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    color: {C_GREEN};
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: {C_ACCENT};
    selection-color: {C_BG};
}}

/* ─── 进度条 ─── */
QProgressBar {{
    border: none;
    border-radius: 6px;
    text-align: center;
    background-color: {C_SURFACE2};
    color: {C_WHITE};
    min-height: 14px;
    font-size: 11px;
    font-weight: bold;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C_ACCENT}, stop:0.5 #82c4f5, stop:1 {C_ACCENT});
    border-radius: 6px;
}}

/* ─── 标签页 ─── */
QTabWidget::pane {{
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    background-color: {C_SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 8px 20px;
    margin-right: 4px;
    color: {C_TEXT_DIM};
    font-weight: bold;
    font-size: 13px;
}}
QTabBar::tab:hover {{
    color: {C_TEXT};
}}
QTabBar::tab:selected {{
    color: {C_ACCENT};
    border-bottom: 3px solid {C_ACCENT};
}}

/* ─── 状态栏 ─── */
QStatusBar {{
    background-color: {C_SURFACE};
    border-top: 1px solid {C_BORDER};
    color: {C_TEXT_DIM};
    font-size: 12px;
    padding: 2px 10px;
}}

/* ─── 分隔线 ─── */
QFrame#separator {{
    background-color: {C_BORDER};
    max-height: 1px;
}}
"""


def _make_shadow(parent, radius=12, offset=(0, 2), color='#00000060'):
    """给控件添加柔和阴影。"""
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(radius)
    shadow.setOffset(*offset)
    shadow.setColor(QColor(color))
    return shadow


def _make_header_banner(parent):
    """创建顶部渐变横幅背景。"""
    banner = QWidget(parent)
    banner.setFixedHeight(72)
    banner.setStyleSheet(f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #1a2f42, stop:0.5 {C_SURFACE}, stop:1 #1a2f42);
        border-bottom: 1px solid {C_BORDER};
    """)
    return banner


class MainWindow(QMainWindow):
    """主窗口 - 精致暗色主题"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.adb = None
        self.img_rec = None
        self.game_analyzer = None
        self.scheduler = None
        self._current_task = None

        self._init_ui()
        self._init_adb()
        self._apply_config()

    # ── UI 构建 ──────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle('明日方舟助手 · MuMu 模拟器版')
        self.setMinimumSize(1020, 700)
        self.resize(1140, 780)
        self.setStyleSheet(GLOBAL_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 顶部横幅 ──
        banner = _make_header_banner(central)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 0, 24, 0)

        # 标题区
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel('明日方舟助手')
        title.setStyleSheet(f'color: {C_WHITE}; font-size: 20px; font-weight: bold; background: transparent; border: none;')
        subtitle = QLabel('MuMu 模拟器自动化  ·  自动刷关 / 基建 / 公招 / 邮件')
        subtitle.setStyleSheet(f'color: {C_TEXT_DIM}; font-size: 12px; background: transparent; border: none;')
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        banner_layout.addLayout(title_col)
        banner_layout.addStretch()

        # 连接状态指示灯
        self.conn_dot = QLabel('●')  # ●
        self.conn_dot.setStyleSheet(f'color: {C_RED}; font-size: 18px; background: transparent; border: none;')
        self.conn_label = QLabel('未连接')
        self.conn_label.setStyleSheet(f'color: {C_TEXT_DIM}; font-size: 13px; background: transparent; border: none; font-weight: bold;')

        conn_row = QHBoxLayout()
        conn_row.setSpacing(6)
        conn_row.addWidget(self.conn_dot)
        conn_row.addWidget(self.conn_label)
        banner_layout.addLayout(conn_row)
        banner_layout.addSpacing(16)

        # 横幅按钮
        self.btn_connect = self._make_banner_btn('⚡ 连接 MuMu')
        self.btn_connect.clicked.connect(self._on_connect)
        banner_layout.addWidget(self.btn_connect)

        btn_template = self._make_banner_btn('✂ 模板工具')
        btn_template.clicked.connect(self._open_template_tool)
        banner_layout.addWidget(btn_template)

        root.addWidget(banner)

        # ── 主内容区域 ──
        content_area = QHBoxLayout()
        content_area.setContentsMargins(16, 16, 16, 0)
        content_area.setSpacing(16)

        # 左侧任务面板
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(360)
        left_scroll.setMaximumWidth(480)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        left_layout.addWidget(self._card_combat())
        left_layout.addWidget(self._card_base())
        left_layout.addWidget(self._card_recruit())
        left_layout.addWidget(self._card_mail())
        left_layout.addWidget(self._card_scheduler())
        left_layout.addStretch()
        left_scroll.setWidget(left_panel)
        content_area.addWidget(left_scroll)

        # 右侧控制面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_log_tab(), '☰  运行日志')
        self.tabs.addTab(self._build_preview_tab(), '▣  截图预览')
        self.tabs.addTab(self._build_settings_tab(), '⚙  设置')
        right_layout.addWidget(self.tabs, 1)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        right_layout.addWidget(self.progress)

        # 底部控制栏
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(f'background: {C_SURFACE}; border: 1px solid {C_BORDER}; border-radius: 10px;')
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(16, 12, 16, 12)
        ctrl_layout.setSpacing(12)

        # 任务计数标签
        self.task_count_label = QLabel('○ 0 个任务就绪')
        self.task_count_label.setStyleSheet(f'color: {C_TEXT_DIM}; font-size: 13px; font-weight: bold;')
        ctrl_layout.addWidget(self.task_count_label)
        ctrl_layout.addStretch()

        self.btn_pause = QPushButton('⏸ 暂停')
        self.btn_pause.setEnabled(False)
        self.btn_pause.setFixedWidth(90)
        self.btn_pause.clicked.connect(self._on_pause)
        ctrl_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton('■ 停止')
        self.btn_stop.setObjectName('btn_stop')
        self.btn_stop.setEnabled(False)
        self.btn_stop.setFixedWidth(90)
        self.btn_stop.clicked.connect(self._on_stop)
        ctrl_layout.addWidget(self.btn_stop)

        self.btn_start = QPushButton('▶  开始运行')
        self.btn_start.setObjectName('btn_start')
        self.btn_start.setFixedWidth(140)
        self.btn_start.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self.btn_start)

        right_layout.addWidget(ctrl_frame)
        content_area.addWidget(right_panel, 1)
        root.addLayout(content_area, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel('✔ 就绪')
        self.status_label.setStyleSheet(f'color: {C_GREEN}; font-weight: bold;')
        self.status_bar.addPermanentWidget(self.status_label)

        # 连接检测定时器
        self._conn_timer = QTimer()
        self._conn_timer.timeout.connect(self._check_connection)
        self._conn_timer.start(5000)

        # 更新任务计数
        self._update_task_count()

    # ── 卡片式任务面板 ───────────────────────────────────────────────────────

    def _card_combat(self):
        """自动刷关卡片"""
        card = QGroupBox('⚔  自动刷关')
        card.setGraphicsEffect(_make_shadow(card))
        cg = QGridLayout(card)
        cg.setSpacing(8)

        self.chk_combat = QCheckBox('启用自动刷关')
        self.chk_combat.stateChanged.connect(self._update_task_count)
        cg.addWidget(self.chk_combat, 0, 0, 1, 2)

        cg.addWidget(QLabel('关卡:'), 1, 0)
        self.combo_stage = QComboBox()
        self.combo_stage.setEditable(True)
        self.combo_stage.addItems([
            'CE-6 — 龙门币', 'LS-6 — 经验', 'CA-5 — 技能书',
            'SK-5 — 碳',   'AP-5 — 芯片',  '1-7 — 固源�ite',
            'S3-7', 'R8-11', 'JT8-3',
        ])
        cg.addWidget(self.combo_stage, 1, 1)

        cg.addWidget(QLabel('次数:'), 2, 0)
        self.spin_times = QSpinBox()
        self.spin_times.setRange(1, 999)
        self.spin_times.setValue(99)
        cg.addWidget(self.spin_times, 2, 1)

        opt_row = QHBoxLayout()
        self.chk_potion = QCheckBox('理智药剂')
        self.chk_originium = QCheckBox('源石补充')
        opt_row.addWidget(self.chk_potion)
        opt_row.addWidget(self.chk_originium)
        cg.addLayout(opt_row, 3, 0, 1, 2)

        return card

    def _card_base(self):
        """基建管理卡片"""
        card = QGroupBox('⌂  基建管理')
        card.setGraphicsEffect(_make_shadow(card))
        bg = QVBoxLayout(card)
        bg.setSpacing(6)

        self.chk_base = QCheckBox('启用基建管理')
        self.chk_base.stateChanged.connect(self._update_task_count)
        bg.addWidget(self.chk_base)

        for text, attr, default in [
            ('自动换班', 'chk_shift', True),
            ('收取制造站 / 贸易站资源', 'chk_collect', True),
            ('处理线索 / 会客室', 'chk_clue', True),
        ]:
            cb = QCheckBox(text)
            cb.setChecked(default)
            setattr(self, attr, cb)
            bg.addWidget(cb)
        return card

    def _card_recruit(self):
        """公开招募卡片"""
        card = QGroupBox('✍  公开招募')
        card.setGraphicsEffect(_make_shadow(card))
        rg = QVBoxLayout(card)
        rg.setSpacing(6)

        self.chk_recruit = QCheckBox('启用公开招募')
        self.chk_recruit.stateChanged.connect(self._update_task_count)
        rg.addWidget(self.chk_recruit)

        self.chk_auto_confirm = QCheckBox('自动确认招募')
        self.chk_auto_confirm.setChecked(True)
        rg.addWidget(self.chk_auto_confirm)

        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel('偏好:'))
        self.edit_tags = QLineEdit('先锋, 近卫, 术师, 治疗')
        self.edit_tags.setPlaceholderText('用逗号分隔')
        tag_row.addWidget(self.edit_tags)
        rg.addLayout(tag_row)
        return card

    def _card_mail(self):
        """邮件收取卡片"""
        card = QGroupBox('✉  邮件收取')
        card.setGraphicsEffect(_make_shadow(card))
        mg = QVBoxLayout(card)
        self.chk_mail = QCheckBox('启用邮件收取')
        self.chk_mail.stateChanged.connect(self._update_task_count)
        mg.addWidget(self.chk_mail)
        return card

    def _card_scheduler(self):
        """定时调度卡片"""
        card = QGroupBox('⏰  定时调度')
        card.setGraphicsEffect(_make_shadow(card))
        sg = QGridLayout(card)
        sg.setSpacing(8)
        self.chk_loop = QCheckBox('循环执行')
        sg.addWidget(self.chk_loop, 0, 0, 1, 2)
        sg.addWidget(QLabel('间隔:'), 1, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 1440)
        self.spin_interval.setValue(5)
        self.spin_interval.setSuffix(' 分钟')
        sg.addWidget(self.spin_interval, 1, 1)
        return card

    # ── 右侧标签页 ──────────────────────────────────────────────────────────

    def _build_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(self.log_text)
        return widget

    def _build_preview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        self.preview_label = QLabel('暂无截图\n\n点击下方按钮截取 MuMu 画面')
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(
            f'background-color: {C_BG}; border: 2px dashed {C_BORDER}; '
            f'border-radius: 10px; color: {C_TEXT_DIM}; font-size: 14px;'
        )
        layout.addWidget(self.preview_label)
        btn = QPushButton('▣  截取 MuMu 画面')
        btn.clicked.connect(self._take_screenshot)
        layout.addWidget(btn)
        return widget

    def _build_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        adb_group = QGroupBox('ADB 连接')
        ag = QGridLayout(adb_group)
        ag.setSpacing(8)
        for row, (label, attr, default) in enumerate([
            ('ADB 路径:',  'edit_adb_path', 'adb'),
            ('主机地址:',  'edit_host',     '127.0.0.1'),
        ]):
            ag.addWidget(QLabel(label), row, 0)
            edit = QLineEdit(default)
            setattr(self, attr, edit)
            ag.addWidget(edit, row, 1)
        ag.addWidget(QLabel('端口:'), 2, 0)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(16384)
        ag.addWidget(self.spin_port, 2, 1)
        layout.addWidget(adb_group)

        ui_group = QGroupBox('界面')
        ug = QVBoxLayout(ui_group)
        self.chk_on_top = QCheckBox('窗口置顶')
        self.chk_on_top.toggled.connect(self._toggle_on_top)
        ug.addWidget(self.chk_on_top)
        layout.addWidget(ui_group)

        btn_row = QHBoxLayout()
        btn_save = QPushButton('\U0001f4be  保存配置')
        btn_save.clicked.connect(self._save_config)
        btn_load = QPushButton('\U0001f4c2  加载配置')
        btn_load.clicked.connect(self._load_config)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_load)
        layout.addLayout(btn_row)

        layout.addStretch()
        return widget

    # ── 辅助方法 ─────────────────────────────────────────────────────────────

    def _make_banner_btn(self, text):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_ACCENT};
                border: none;
                color: {C_BG};
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: #82c4f5; }}
            QPushButton:pressed {{ background-color: #4a9fd4; }}
        """)
        return btn

    def _update_task_count(self):
        count = sum([
            self.chk_combat.isChecked(),
            self.chk_base.isChecked(),
            self.chk_recruit.isChecked(),
            self.chk_mail.isChecked(),
        ])
        if count > 0:
            self.task_count_label.setText(f'● {count} 个任务就绪')
            self.task_count_label.setStyleSheet(f'color: {C_GREEN}; font-size: 13px; font-weight: bold;')
        else:
            self.task_count_label.setText(f'○ 未选择任务')
            self.task_count_label.setStyleSheet(f'color: {C_TEXT_DIM}; font-size: 13px; font-weight: bold;')

    # ── 初始化 / 配置 ───────────────────────────────────────────────────────

    def _init_adb(self):
        adb_cfg = self.config.get('adb', {})
        adb_path = adb_cfg.get('path', '')
        if not adb_path or adb_path == 'adb':
            adb_path = find_mumu_adb()
            self.edit_adb_path.setText(adb_path)
        self.adb = ADBController(
            adb_path=adb_path,
            host=adb_cfg.get('host', '127.0.0.1'),
            port=adb_cfg.get('port', 16384),
        )
        self.img_rec = ImageRecognition(assets_dir=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'images'
        ))
        self.action_memory = ActionMemory()
        self.game_analyzer = GameAnalyzer(self.img_rec, action_memory=self.action_memory)

    def _apply_config(self):
        adb = self.config.get('adb', {})
        self.edit_adb_path.setText(adb.get('path', 'adb'))
        self.edit_host.setText(adb.get('host', '127.0.0.1'))
        self.spin_port.setValue(adb.get('port', 16384))

        tasks = self.config.get('tasks', {})
        combat = tasks.get('combat', {})
        self.chk_combat.setChecked(combat.get('enabled', False))
        self.combo_stage.setCurrentText(combat.get('stage', 'CE-6'))
        self.spin_times.setValue(combat.get('times', 99))
        self.chk_potion.setChecked(combat.get('use_sanity_potion', False))
        self.chk_originium.setChecked(combat.get('use_originium', False))

        base = tasks.get('base', {})
        self.chk_base.setChecked(base.get('enabled', False))
        self.chk_shift.setChecked(base.get('auto_shift', True))
        self.chk_collect.setChecked(base.get('auto_collect', True))
        self.chk_clue.setChecked(base.get('auto_clue', True))

        recruit = tasks.get('recruitment', {})
        self.chk_recruit.setChecked(recruit.get('enabled', False))
        self.chk_auto_confirm.setChecked(recruit.get('auto_confirm', True))
        self.edit_tags.setText(', '.join(recruit.get('preferred_tags', [])))

        mail = tasks.get('mail', {})
        self.chk_mail.setChecked(mail.get('enabled', False))

        sched = self.config.get('scheduler', {})
        self.chk_loop.setChecked(sched.get('enabled', False))
        self.spin_interval.setValue(sched.get('loop_interval', 300) // 60)
        self._update_task_count()

    def _gather_config(self):
        return {
            'adb': {
                'path': self.edit_adb_path.text(),
                'host': self.edit_host.text(),
                'port': self.spin_port.value(),
            },
            'tasks': {
                'combat': {
                    'enabled': self.chk_combat.isChecked(),
                    'stage': self.combo_stage.currentText(),
                    'times': self.spin_times.value(),
                    'use_sanity_potion': self.chk_potion.isChecked(),
                    'use_originium': self.chk_originium.isChecked(),
                },
                'base': {
                    'enabled': self.chk_base.isChecked(),
                    'auto_shift': self.chk_shift.isChecked(),
                    'auto_collect': self.chk_collect.isChecked(),
                    'auto_clue': self.chk_clue.isChecked(),
                },
                'recruitment': {
                    'enabled': self.chk_recruit.isChecked(),
                    'auto_confirm': self.chk_auto_confirm.isChecked(),
                    'preferred_tags': [t.strip() for t in self.edit_tags.text().split(',') if t.strip()],
                },
                'mail': {'enabled': self.chk_mail.isChecked()},
            },
            'scheduler': {
                'enabled': self.chk_loop.isChecked(),
                'loop_interval': self.spin_interval.value() * 60,
            },
        }

    # ── 事件处理 ─────────────────────────────────────────────────────────────

    def _on_connect(self):
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText('连接中...')
        self.conn_dot.setStyleSheet(f'color: {C_YELLOW}; font-size: 18px; background: transparent; border: none;')
        self.conn_label.setText('连接中...')
        self.conn_label.setStyleSheet(f'color: {C_YELLOW}; font-size: 13px; background: transparent; border: none; font-weight: bold;')
        # 强制刷新界面，防止卡死
        QApplication.processEvents()

        self._log('info', '正在扫描 MuMu 实例...')
        adb_path = self.edit_adb_path.text()
        host, port, success = connect_mumu(adb_path, instance=0)
        if success:
            self.adb.host = host
            self.adb.port = port
            self.adb.device = f'{host}:{port}'
            self.adb.connected = True
            self.edit_host.setText(host)
            self.spin_port.setValue(port)
            self._update_conn_status(True)
            self._log('info', f'MuMu 已连接 ({host}:{port})')
        else:
            host = self.edit_host.text()
            port = self.spin_port.value()
            self.adb.host = host
            self.adb.port = port
            self.adb.device = f'{host}:{port}'
            self._log('info', f'尝试手动连接 ({host}:{port})...')
            success = self.adb.connect()
            self._update_conn_status(success)
            if success:
                self._log('info', 'MuMu 连接成功！')
            else:
                self._log('error', '连接失败，请确认 MuMu 已启动')

        self.btn_connect.setEnabled(True)
        self.btn_connect.setText('⚡ 连接 MuMu')

    def _open_template_tool(self):
        if not self.adb.connected:
            QMessageBox.warning(self, '提示', '请先连接 MuMu 模拟器！')
            return
        from ui.template_tool import TemplateToolDialog
        assets_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'images'
        )
        dlg = TemplateToolDialog(self.adb, assets_dir, parent=self)
        dlg.exec_()

    def _on_start(self):
        self.config = self._gather_config()
        self._create_and_start_tasks()

    def _create_and_start_tasks(self):
        task_params = (self.adb, self.img_rec, self.game_analyzer, self.config)
        tasks = []
        if self.chk_combat.isChecked():
            tasks.append(CombatTask(*task_params))
        if self.chk_base.isChecked():
            tasks.append(BaseManagementTask(*task_params))
        if self.chk_recruit.isChecked():
            tasks.append(RecruitmentTask(*task_params))
        if self.chk_mail.isChecked():
            tasks.append(MailTask(*task_params))
        if not tasks:
            self._log('warning', '未选择任何任务！')
            return

        self.scheduler = TaskScheduler(self.config, action_memory=self.action_memory)
        for task in tasks:
            task.log_signal.connect(self._on_task_log)
            task.progress_signal.connect(self._on_task_progress)
            task.status_signal.connect(self._on_task_status)
            task.finished_signal.connect(self._on_task_finished)
            self.scheduler.add_task(task)

        sched_cfg = self.config.get('scheduler', {})
        self.scheduler.set_loop(sched_cfg.get('enabled', False), sched_cfg.get('loop_interval', 300))
        self.scheduler.log_signal.connect(self._on_task_log)
        self.scheduler.status_signal.connect(self._on_task_status)
        self.scheduler.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.status_label.setText('▶ 运行中...')
        self.status_label.setStyleSheet(f'color: {C_GREEN}; font-weight: bold;')
        self._log('info', f'已启动 {len(tasks)} 个任务')

    def _on_stop(self):
        self._log('info', '正在停止所有任务...')
        QApplication.processEvents()
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler.wait(5000)
            if self.scheduler.isRunning():
                self.scheduler.terminate()
                self.scheduler.wait(1000)
            self.scheduler = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText('⏸ 暂停')
        self.progress.setValue(0)
        self.status_label.setText('✔ 就绪')
        self.status_label.setStyleSheet(f'color: {C_GREEN}; font-weight: bold;')
        self._log('info', '所有任务已停止')

    def _on_pause(self):
        if not self.scheduler:
            return
        self.scheduler.pause()
        if self.scheduler.is_paused():
            self.btn_pause.setText('▶ 继续')
            self.status_label.setText('⏸ 已暂停')
            self.status_label.setStyleSheet(f'color: {C_YELLOW}; font-weight: bold;')
            self._log('info', '任务已暂停')
        else:
            self.btn_pause.setText('⏸ 暂停')
            self.status_label.setText('▶ 运行中...')
            self.status_label.setStyleSheet(f'color: {C_GREEN}; font-weight: bold;')
            self._log('info', '任务已继续')

    def _on_task_log(self, level, message):
        self._log(level, message)

    def _on_task_progress(self, current, total):
        if total > 0:
            self.progress.setValue(int(current / total * 100))

    def _on_task_status(self, status):
        self.status_label.setText(f'▶ {status}')

    def _on_task_finished(self, success, message):
        self._log('info' if success else 'warning', message)

    def _take_screenshot(self):
        if not self.adb.connected:
            self._log('warning', '未连接 MuMu')
            return
        try:
            screen = self.adb.screenshot()
            h, w = screen.shape[:2]
            rgb = screen[:, :, ::-1].copy()
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
            self._log('info', f'截图完成 ({w}x{h})')
        except Exception as e:
            self._log('error', f'截图失败: {e}')

    def _toggle_on_top(self, checked):
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _check_connection(self):
        if self.adb and self.adb.connected:
            if not self.adb.is_connected():
                self.adb.connected = False
                self._update_conn_status(False)
                self._log('warning', 'MuMu 连接已断开！')

    def _update_conn_status(self, connected):
        if connected:
            self.conn_dot.setStyleSheet(f'color: {C_GREEN}; font-size: 18px; background: transparent; border: none;')
            self.conn_label.setText('已连接')
            self.conn_label.setStyleSheet(f'color: {C_GREEN}; font-size: 13px; background: transparent; border: none; font-weight: bold;')
        else:
            self.conn_dot.setStyleSheet(f'color: {C_RED}; font-size: 18px; background: transparent; border: none;')
            self.conn_label.setText('未连接')
            self.conn_label.setStyleSheet(f'color: {C_TEXT_DIM}; font-size: 13px; background: transparent; border: none; font-weight: bold;')

    def _log(self, level, message):
        colors = {
            'debug':   C_TEXT_DIM,
            'info':    C_GREEN,
            'warning': C_YELLOW,
            'error':   C_RED,
        }
        color = colors.get(level, C_TEXT)
        self.log_text.append(
            f'<span style="color:{C_TEXT_DIM}">[{level.upper()}]</span> '
            f'<span style="color:{color}">{message}</span>'
        )
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _save_config(self):
        config = self._gather_config()
        path, _ = QFileDialog.getSaveFileName(self, '保存配置', 'config.json', 'JSON (*.json)')
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._log('info', f'配置已保存: {path}')

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, '加载配置', '', 'JSON (*.json)')
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self._apply_config()
            self._init_adb()
            self._log('info', f'配置已加载: {path}')

    def closeEvent(self, event):
        if self.scheduler and self.scheduler.isRunning():
            self.scheduler.stop()
            self.scheduler.wait(3000)
        if self.adb and self.adb.connected:
            self.adb.disconnect()
        event.accept()
