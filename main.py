"""Arknights Assistant - MuMu Edition.

Game automation tool for Arknights via MuMu emulator (ADB).
Features: auto combat, base management, recruitment, mail collection.
"""
import json
import sys
import os
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'


def setup_logging(level='INFO'):
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('arknights_assistant.log', encoding='utf-8'),
        ]
    )


def load_config(path='config.json'):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    config = load_config()
    setup_logging(config.get('ui', {}).get('log_level', 'INFO'))

    app = QApplication(sys.argv)
    app.setApplicationName('Arknights Assistant')
    app.setFont(QFont('Microsoft YaHei', 10))

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
