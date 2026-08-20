# Arknights Assistant - MuMu Edition

明日方舟自动化助手，基于 MuMu 模拟器 ADB 控制。

> 当前仓库是个人实验项目。请先确认模拟器、ADB 地址和任务开关，再运行自动化任务。

## Features

- Auto combat with sanity management
- Base management
- Recruitment tag analysis
- Mail collection
- Scheduled task loop
- MuMu emulator preset configuration

## Requirements

- Python 3.9+
- MuMu Player
- MuMu bundled ADB or Android platform-tools
- PyQt5, OpenCV, NumPy, Pillow

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.json` before the first run:

- `adb.path`: set this to the ADB executable on your machine.
- `adb.host` and `adb.port`: match the MuMu instance.
- `adb.auto_connect`: disable automatic connection if the emulator is not always available.
- Keep task switches disabled until the UI and ADB connection have been verified.

The checked-in configuration contains a machine-specific path as an example. Replace it locally and avoid committing personal emulator paths.

## MuMu ADB Setup

1. Enable ADB in MuMu: Settings → Other → Open ADB debugging.
2. Confirm the instance address, commonly `127.0.0.1:16384` for MuMu 12 instance 0.
3. Update `config.json` with the ADB path and address for your machine.
4. Verify the connection before enabling scheduled or combat tasks.

## Run

```bash
python main.py
```

## Project Structure

```
arknights-assistant/
├── main.py                  # Entry point
├── config.json              # Local emulator and task configuration
├── requirements.txt         # Python dependencies
├── core/                    # ADB, image recognition, and game state
├── tasks/                   # Combat, base, recruitment, mail, scheduler
├── ui/main_window.py        # PyQt5 UI
└── assets/                  # Template images
```

## Safety Notes

- Test with all task switches disabled first.
- Do not enable automatic confirmation or resource spending until the flow is verified.
- Do not commit local emulator paths, credentials, screenshots with personal information, or private logs.
