"""Auto-detect MuMu emulator installation and ADB path."""
import glob
import json
import logging
import os
import subprocess
import time
import winreg

logger = logging.getLogger(__name__)

# Common MuMu installation paths
MUMU_PATHS = [
    r'E:\MuMuPlayer-12.0',
    r'C:\Program Files\Netease\MuMuPlayer-12.0',
    r'C:\Program Files\Netease\MuMuPlayer-12',
    r'C:\Program Files\MuMuPlayer-12.0',
    r'D:\MuMuPlayer-12.0',
    r'F:\MuMuPlayer-12.0',
    r'D:\Program Files\Netease\MuMuPlayer-12.0',
    r'D:\Program Files\Netease\MuMuPlayer-12',
    r'C:\Program Files (x86)\Netease\MuMuPlayer-12.0',
    os.path.expanduser(r'~\AppData\Local\Programs\MuMuPlayer-12.0'),
    os.path.expanduser(r'~\AppData\Local\MuMuPlayer'),
]

ADB_RELATIVE_PATHS = [
    r'nx_device\12.0\shell\adb.exe',
    r'nx_main\adb.exe',
    r'shell\adb.exe',
]

# MuMu ADB port mapping (instance -> port)
MUMU_PORT_MAP = {
    0: 16384,   # MuMu 12 default instance
    1: 16416,
    2: 16448,
    3: 16480,
}


def _search_registry():
    """Search Windows registry for MuMu installation path."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                display_name = winreg.QueryValueEx(subkey, 'DisplayName')[0]
                if 'MuMu' in display_name or 'mumu' in display_name.lower():
                    install_loc = winreg.QueryValueEx(subkey, 'InstallLocation')[0]
                    if install_loc and os.path.exists(install_loc):
                        logger.info(f'Found MuMu via registry: {install_loc}')
                        return install_loc
            except (FileNotFoundError, OSError):
                continue
    except Exception:
        pass
    return None


def _search_drives():
    """Search common drive letters for MuMu installation."""
    for drive in ['C:', 'D:', 'E:', 'F:']:
        for pattern in [
            rf'{drive}\MuMuPlayer*',
            rf'{drive}\Program Files\Netease\MuMuPlayer*',
            rf'{drive}\Program Files\MuMuPlayer*',
            rf'{drive}\Program Files (x86)\Netease\MuMuPlayer*',
            rf'{drive}\Netease\MuMuPlayer*',
        ]:
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    logger.info(f'Found MuMu via drive scan: {path}')
                    return path
    return None


def _find_adb_under(mumu_path):
    """Return the first known MuMu ADB path under an install root."""
    if not mumu_path:
        return None
    for relative_path in ADB_RELATIVE_PATHS:
        adb_path = os.path.join(mumu_path, relative_path)
        if os.path.exists(adb_path):
            return adb_path
    return None


def find_mumu_root():
    """Find the MuMu installation root."""
    for mumu_path in MUMU_PATHS:
        if os.path.exists(mumu_path):
            return mumu_path
    return _search_registry() or _search_drives()


def find_mumu_cli():
    """Find MuMu 12's mumu-cli executable."""
    mumu_root = find_mumu_root()
    if not mumu_root:
        return None
    cli_path = os.path.join(mumu_root, 'nx_main', 'mumu-cli.exe')
    return cli_path if os.path.exists(cli_path) else None


def find_mumu_adb():
    """Find MuMu's bundled ADB executable."""
    # Search known paths
    for mumu_path in MUMU_PATHS:
        adb_path = _find_adb_under(mumu_path)
        if adb_path:
            logger.info(f'Found MuMu ADB: {adb_path}')
            return adb_path

    # Search registry
    reg_path = _search_registry()
    if reg_path:
        adb_path = _find_adb_under(reg_path)
        if adb_path:
            return adb_path

    # Search drives
    drive_path = _search_drives()
    if drive_path:
        adb_path = _find_adb_under(drive_path)
        if adb_path:
            return adb_path

    # Fallback: check if adb is in PATH
    try:
        result = subprocess.run(
            ['where', 'adb'], capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            adb_path = result.stdout.decode().strip().split('\n')[0]
            logger.info(f'Found ADB in PATH: {adb_path}')
            return adb_path
    except Exception:
        pass

    logger.warning('MuMu ADB not found, using default "adb"')
    return 'adb'


def find_mumu_instance_port(instance=0):
    """Find the ADB port for a MuMu instance."""
    port = 16384 + instance * 32
    return port


def _run_hidden(cmd, timeout=10):
    """Run a command without opening a console window."""
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _read_mumu_info(cli_path, instance=0):
    """Read one MuMu instance's JSON status through mumu-cli."""
    result = _run_hidden([cli_path, 'info', '--vmindex', str(instance)], timeout=10)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout.decode('utf-8', errors='ignore'))


def ensure_mumu_started(instance=0, wait_seconds=120):
    """Start MuMu if needed and wait until Android is ready."""
    cli_path = find_mumu_cli()
    if not cli_path:
        return False

    try:
        info = _read_mumu_info(cli_path, instance)
        if info and info.get('is_android_started'):
            return True

        logger.info(f'Launching MuMu instance {instance}')
        _run_hidden(
            [cli_path, 'control', '--vmindex', str(instance), 'launch'],
            timeout=15,
        )

        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(3)
            info = _read_mumu_info(cli_path, instance)
            if info and info.get('is_android_started'):
                return True
    except Exception as exc:
        logger.warning(f'MuMu startup check failed: {exc}')

    return False


def detect_mumu_instances(adb_path='adb'):
    """Detect running MuMu instances by querying ADB devices."""
    try:
        result = _run_hidden([adb_path, 'devices'], timeout=10)
        devices = []
        for line in result.stdout.decode().strip().split('\n')[1:]:
            line = line.strip()
            if line and '\t' in line:
                serial, state = line.split('\t')
                if '127.0.0.1' in serial:
                    devices.append({
                        'serial': serial,
                        'state': state,
                        'port': int(serial.split(':')[1]) if ':' in serial else 7555,
                    })
        return devices
    except Exception as e:
        logger.error(f'Failed to detect devices: {e}')
        return []


def connect_mumu(adb_path='adb', instance=0):
    """Connect to a specific MuMu instance. Returns (host, port, success)."""
    host = '127.0.0.1'
    port = find_mumu_instance_port(instance)

    cli_path = find_mumu_cli()
    if cli_path:
        ensure_mumu_started(instance=instance)

        try:
            result = _run_hidden(
                [cli_path, 'adb', '--vmindex', str(instance), '--cmd', 'connect'],
                timeout=30,
            )
            output = result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'adb_port' in output:
                payload = json.loads(output)
                port = int(payload.get('adb_port', port))
            else:
                logger.debug(f'mumu-cli adb connect output: {output.strip()}')
        except Exception as exc:
            logger.warning(f'MuMu CLI adb connect failed: {exc}')

    # Try MuMu 12 default or CLI-reported port first.
    try:
        _run_hidden([adb_path, 'connect', f'{host}:{port}'], timeout=10)
        result = _run_hidden([adb_path, '-s', f'{host}:{port}', 'get-state'], timeout=5)
        if result.stdout.decode().strip() == 'device':
            logger.info(f'Connected to MuMu instance {instance} at {host}:{port}')
            return host, port, True
    except Exception:
        pass

    # Fallback: try common ports
    for fallback_port in [7555, 7556, 7557, 16384, 16416]:
        if fallback_port == port:
            continue
        try:
            _run_hidden([adb_path, 'connect', f'{host}:{fallback_port}'], timeout=5)
            result = _run_hidden(
                [adb_path, '-s', f'{host}:{fallback_port}', 'get-state'],
                timeout=5,
            )
            if result.stdout.decode().strip() == 'device':
                logger.info(f'Connected to MuMu at {host}:{fallback_port}')
                return host, fallback_port, True
        except Exception:
            continue

    logger.error('Failed to connect to any MuMu instance')
    return host, port, False


def get_mumu_info():
    """Get comprehensive MuMu installation info."""
    adb_path = find_mumu_adb()
    devices = detect_mumu_instances(adb_path)
    mumu_path = find_mumu_root()
    return {
        'adb_path': adb_path,
        'devices': devices,
        'mumu_path': mumu_path,
        'mumu_cli': find_mumu_cli(),
    }
