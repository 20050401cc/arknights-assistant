"""模板截图裁剪工具 - 用于创建游戏模板图片"""
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QGroupBox,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor

from core.adb_controller import ADBController


class CropLabel(QLabel):
    """Label that supports drag-to-crop rectangle selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start = None
        self._end = None
        self._selecting = False
        self._base_pixmap = None
        self.setMinimumSize(640, 360)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('background-color: #0d1117; border: 1px solid #0f3460;')

    def set_base_pixmap(self, pixmap):
        self._base_pixmap = pixmap
        self._start = None
        self._end = None
        self._update_display()

    def get_selection_rect(self):
        if self._start and self._end:
            return QRect(self._start, self._end).normalized()
        return None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._base_pixmap:
            self._start = self._to_image_pos(ev.pos())
            self._end = self._start
            self._selecting = True

    def mouseMoveEvent(self, ev):
        if self._selecting:
            self._end = self._to_image_pos(ev.pos())
            self._update_display()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._selecting = False
            self._end = self._to_image_pos(ev.pos())
            self._update_display()

    def _to_image_pos(self, widget_pos):
        if not self._base_pixmap:
            return widget_pos
        # Map widget coordinates to image coordinates
        pw = self._base_pixmap.width()
        ph = self._base_pixmap.height()
        lw = self.width()
        lh = self.height()
        # Account for alignment (center)
        offset_x = (lw - pw) // 2
        offset_y = (lh - ph) // 2
        ix = int((widget_pos.x() - offset_x) * pw / pw) if pw > 0 else widget_pos.x()
        iy = int((widget_pos.y() - offset_y) * ph / ph) if ph > 0 else widget_pos.y()
        # Scale if pixmap is scaled
        scaled = self._base_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        sx = scaled.width()
        sy = scaled.height()
        ox = (lw - sx) / 2
        oy = (lh - sy) / 2
        ix = max(0, min(pw, int((widget_pos.x() - ox) * pw / sx))) if sx > 0 else 0
        iy = max(0, min(ph, int((widget_pos.y() - oy) * ph / sy))) if sy > 0 else 0
        return QPoint(ix, iy)

    def _update_display(self):
        if not self._base_pixmap:
            return
        display = self._base_pixmap.copy()
        painter = QPainter(display)
        rect = self.get_selection_rect()
        if rect:
            pen = QPen(QColor(233, 69, 96), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            # Draw size label
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.x(), rect.y() - 5,
                             f'{rect.width()}x{rect.height()}')
        painter.end()
        scaled = display.scaled(
            self.size(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(scaled)


class TemplateToolDialog(QDialog):
    """Dialog for capturing and cropping template images from MuMu."""

    def __init__(self, adb: ADBController, assets_dir='assets/images', parent=None):
        super().__init__(parent)
        self.adb = adb
        self.assets_dir = assets_dir
        self._cv_image = None
        self.setWindowTitle('模板截图工具')
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Screenshot display
        self.crop_label = CropLabel()
        layout.addWidget(self.crop_label, 1)

        # Controls
        ctrl = QHBoxLayout()
        btn_capture = QPushButton('截取 MuMu 画面')
        btn_capture.clicked.connect(self._capture)
        ctrl.addWidget(btn_capture)

        btn_load = QPushButton('加载本地图片')
        btn_load.clicked.connect(self._load_image)
        ctrl.addWidget(btn_load)

        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Save controls
        save_group = QGroupBox('保存为模板')
        sg = QHBoxLayout(save_group)
        sg.addWidget(QLabel('名称:'))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText('例如: nav_combat')
        sg.addWidget(self.edit_name)
        btn_save = QPushButton('保存选区')
        btn_save.clicked.connect(self._save_selection)
        sg.addWidget(btn_save)
        layout.addWidget(save_group)

        # Preset names
        presets = QGroupBox('快速预设模板名')
        pl = QHBoxLayout(presets)
        preset_names = [
            'nav_combat', 'nav_base', 'nav_recruit', 'combat_start_b',
            'combat_result_s', 'combat_failed_s', 'confirm_b', 'mail_icon',
            'sanity_recover', 'ann_c', 'net_error', 'recruit_slot_empty',
        ]
        for name in preset_names:
            btn = QPushButton(name)
            btn.setMaximumWidth(120)
            btn.clicked.connect(lambda checked, n=name: self.edit_name.setText(n))
            pl.addWidget(btn)
        scroll = QScrollArea()
        scroll.setWidget(presets)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(70)
        layout.addWidget(scroll)

    def _capture(self):
        if not self.adb.connected:
            QMessageBox.warning(self, '提示', '未连接 MuMu')
            return
        try:
            cv_img = self.adb.screenshot()
            self._cv_image = cv_img
            h, w = cv_img.shape[:2]
            rgb = cv_img[:, :, ::-1].copy()
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.crop_label.set_base_pixmap(pixmap)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'截图失败: {e}')

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '加载图片', '', '图片文件 (*.png *.jpg *.bmp)')
        if path:
            cv_img = cv2.imread(path)
            if cv_img is None:
                QMessageBox.warning(self, '错误', '加载图片失败')
                return
            self._cv_image = cv_img
            h, w = cv_img.shape[:2]
            rgb = cv_img[:, :, ::-1].copy()
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.crop_label.set_base_pixmap(pixmap)

    def _save_selection(self):
        if self._cv_image is None:
            QMessageBox.warning(self, '提示', '请先截图或加载图片')
            return
        rect = self.crop_label.get_selection_rect()
        if not rect:
            QMessageBox.warning(self, '提示', '请先拖框选择区域')
            return
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, '提示', '请输入模板名称')
            return

        # Crop from cv image
        h, w = self._cv_image.shape[:2]
        x1 = max(0, rect.x())
        y1 = max(0, rect.y())
        x2 = min(w, rect.x() + rect.width())
        y2 = min(h, rect.y() + rect.height())
        crop = self._cv_image[y1:y2, x1:x2]

        if crop.size == 0:
            QMessageBox.warning(self, '提示', '选区为空')
            return

        # Save
        os.makedirs(self.assets_dir, exist_ok=True)
        out_path = os.path.join(self.assets_dir, f'{name}.png')
        cv2.imwrite(out_path, crop)
        QMessageBox.information(self, '保存成功',
                                f'模板已保存: {out_path}\n尺寸: {crop.shape[1]}x{crop.shape[0]}')
