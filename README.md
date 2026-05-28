# Arknights Assistant - MuMu Edition

明日方舟自动化助手，基于 MuMu 模拟器 ADB 控制。

## Features

- Auto combat (stage farming with sanity management)
- Base management (operator shift, resource collection, clue exchange)
- Recruitment (tag analysis, optimal selection)
- Mail collection
- Scheduled task loop
- MuMu emulator preset configuration

## Requirements

- Python 3.9+
- MuMu Player (网易MuMu模拟器)
- ADB (MuMu bundled or platform-tools)

## Install

```bash
pip install -r requirements.txt
```

## MuMu ADB Setup

1. Enable ADB in MuMu: Settings -> Other -> Open ADB debugging
2. This machine uses MuMu 12 instance `0`, ADB address: `127.0.0.1:16384`
3. MuMu's bundled ADB path on this machine:
   `E:\MuMuPlayer-12.0\nx_device\12.0\shell\adb.exe`
4. The assistant now uses `mumu-cli.exe` to start instance `0` and connect ADB automatically.

## Run

```bash
python main.py
```

## Project Structure

```
arknights-assistant/
├── main.py                  # Entry point
├── config.json              # Configuration
├── requirements.txt         # Dependencies
├── core/
│   ├── adb_controller.py    # ADB connection (MuMu optimized)
│   ├── image_recognition.py # OpenCV template matching
│   └── game_state.py        # Game state detection
├── tasks/
│   ├── base_task.py         # Base task class
│   ├── combat_task.py       # Auto combat/farming
│   ├── base_management.py   # Base operations
│   ├── recruitment_task.py  # Auto recruitment
│   ├── mail_task.py         # Mail collection
│   └── scheduler.py         # Task scheduler
├── ui/
│   └── main_window.py       # PyQt6 dark theme UI
└── assets/
    └── images/              # Template images for matching
```

## Adding Template Images

Place game screenshots as `.png` files in `assets/images/` for template matching:

- `nav_combat.png` - Combat navigation button
- `nav_base.png` - Base navigation button
- `nav_recruit.png` - Recruitment button
- `combat_start_b.png` - Start battle button
- `combat_result_s.png` - Battle result screen indicator
- `confirm_b.png` - Confirm button
- `mail_icon.png` - Mail icon
- `sanity_recover.png` - Sanity recovery button

Use the Preview tab to capture MuMu screenshots and crop the needed regions.
