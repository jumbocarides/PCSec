import os
import sys
import json
import time
import socket
import logging
import threading
from datetime import datetime
from pathlib import Path
import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32gui
import win32process

from dotenv import load_dotenv

from email.message import EmailMessage
import smtplib
import ssl

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QLinearGradient

import cv2
import numpy as np
import sounddevice as sd
import soundfile as sf
import pyautogui
from PIL import ImageGrab

# ----------------------------
# Windows Security Functions
# ----------------------------

# Windows API constants
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Hook constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0

# Virtual key codes for system keys
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_DELETE = 0x2E
VK_F4 = 0x73
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

# Global hook handle
hook_id = None

def low_level_keyboard_proc(nCode, wParam, lParam):
    """Low-level keyboard hook procedure to block system keys"""
    if nCode == HC_ACTION:
        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            kbd_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk_code = kbd_struct.vkCode
            
            # Block dangerous key combinations
            ctrl_pressed = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
            alt_pressed = user32.GetAsyncKeyState(VK_MENU) & 0x8000
            
            # Block Ctrl+Alt+Del, Ctrl+Shift+Esc, Alt+Tab, Win keys, etc.
            if (
                (ctrl_pressed and alt_pressed and vk_code == VK_DELETE) or  # Ctrl+Alt+Del
                (alt_pressed and vk_code == VK_TAB) or  # Alt+Tab
                (alt_pressed and vk_code == VK_F4) or  # Alt+F4
                vk_code in (VK_LWIN, VK_RWIN) or  # Windows keys
                (ctrl_pressed and vk_code == VK_ESCAPE)  # Ctrl+Esc
            ):
                logger.info(f"Blocked system key combination: VK={vk_code}, Ctrl={ctrl_pressed}, Alt={alt_pressed}")
                return 1  # Block the key
    
    return user32.CallNextHookExW(hook_id, nCode, wParam, lParam)

def install_keyboard_hook():
    """Install low-level keyboard hook"""
    global hook_id
    try:
        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        hook_proc = HOOKPROC(low_level_keyboard_proc)
        hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            hook_proc,
            kernel32.GetModuleHandleW(None),
            0
        )
        if hook_id:
            logger.info("Keyboard hook installed successfully")
            return True
        else:
            logger.error("Failed to install keyboard hook")
            return False
    except Exception as e:
        logger.error(f"Error installing keyboard hook: {e}")
        return False

def uninstall_keyboard_hook():
    """Uninstall keyboard hook"""
    global hook_id
    if hook_id:
        user32.UnhookWindowsHookEx(hook_id)
        hook_id = None
        logger.info("Keyboard hook uninstalled")

def disable_task_manager():
    """Disable Task Manager via registry"""
    try:
        import winreg
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
        winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        logger.info("Task Manager disabled")
    except Exception as e:
        logger.error(f"Failed to disable Task Manager: {e}")

def enable_task_manager():
    """Re-enable Task Manager"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "DisableTaskMgr")
        winreg.CloseKey(key)
        logger.info("Task Manager enabled")
    except Exception as e:
        logger.error(f"Failed to enable Task Manager: {e}")

# ----------------------------
# Paths and configuration load
# ----------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

CAPTURES_DIR = BASE_DIR / 'captures'
LOGS_DIR = BASE_DIR / 'logs'
CONFIG_FILE = BASE_DIR / 'config.json'
ENV_FILE = BASE_DIR / 'gmail_config.env'

CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Enhanced Logging with rotation
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup enhanced logging with rotation and detailed formatting"""
    # Create custom formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (max 10MB, keep 5 files)
    file_handler = RotatingFileHandler(
        LOGS_DIR / 'activity.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler with colors for different levels
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger('securelock')

logger = setup_logging()

# Load config
DEFAULT_CONFIG = {
    "unlock_mode": "key",
    "unlock_key": "F12",
    "safe_key": "Y",
    "unlock_passcode": "123456",
    "camera_enabled": False,
    "audio_enabled": False,
    "audio_seconds": 5,
    "screenshot_enabled": True,
    "email_enabled": False,
    "mail_attach_media": True,
    "cooldown_seconds_between_captures": 30,
    "show_consent_banner": True,
    "mouse_triggers_enabled": True,
    "security_mode_enabled": True,
    "disable_task_manager": False,
    "block_system_keys": True,
    "ui_theme": "dark",
    "show_animations": True,
    "include_system_info": True
}

def validate_config(config: dict) -> dict:
    """Validate and sanitize configuration"""
    validated = DEFAULT_CONFIG.copy()
    
    # Validate unlock_mode
    if config.get('unlock_mode') in ['key', 'passcode']:
        validated['unlock_mode'] = config['unlock_mode']
    else:
        logger.warning(f"Invalid unlock_mode: {config.get('unlock_mode')}, using default 'key'")
    
    # Validate unlock_key
    if 'unlock_key' in config:
        key = str(config['unlock_key']).strip()
        if to_qt_key(key) is not None or key == "":
            validated['unlock_key'] = key
        else:
            logger.warning(f"Invalid unlock_key: {key}, using default")
    
    # Validate passcode
    if 'unlock_passcode' in config:
        passcode = str(config['unlock_passcode'])
        if len(passcode) >= 4:
            validated['unlock_passcode'] = passcode
        else:
            logger.warning("Passcode too short, using default")
    
    # Validate boolean settings
    bool_settings = [
        'camera_enabled', 'audio_enabled', 'screenshot_enabled', 'email_enabled',
        'mail_attach_media', 'show_consent_banner', 'mouse_triggers_enabled',
        'security_mode_enabled', 'disable_task_manager', 'block_system_keys',
        'show_animations', 'include_system_info'
    ]
    
    for setting in bool_settings:
        if setting in config and isinstance(config[setting], bool):
            validated[setting] = config[setting]
    
    # Validate numeric settings
    if 'audio_seconds' in config:
        try:
            seconds = int(config['audio_seconds'])
            if 1 <= seconds <= 60:
                validated['audio_seconds'] = seconds
            else:
                logger.warning(f"Invalid audio_seconds: {seconds}, using default")
        except (ValueError, TypeError):
            logger.warning(f"Invalid audio_seconds type: {config['audio_seconds']}")
    
    if 'cooldown_seconds_between_captures' in config:
        try:
            cooldown = int(config['cooldown_seconds_between_captures'])
            if 0 <= cooldown <= 3600:
                validated['cooldown_seconds_between_captures'] = cooldown
            else:
                logger.warning(f"Invalid cooldown: {cooldown}, using default")
        except (ValueError, TypeError):
            logger.warning(f"Invalid cooldown type: {config['cooldown_seconds_between_captures']}")
    
    # Validate theme
    if config.get('ui_theme') in ['dark', 'light']:
        validated['ui_theme'] = config['ui_theme']
    
    # Validate safe_key
    if 'safe_key' in config:
        key = str(config['safe_key']).strip().upper()
        if len(key) == 1 and key.isalnum():
            validated['safe_key'] = key
        else:
            logger.warning(f"Invalid safe_key: {key}, using default")
    
    return validated

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return validate_config(cfg)
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON hatası: {e}")
        except Exception as e:
            logger.error(f"Config okunamadı: {e}")
    else:
        logger.info("Config dosyası bulunamadı, varsayılan ayarlar kullanılıyor")
        # Create default config file
        save_config(DEFAULT_CONFIG)
    
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Config kaydedildi: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Config kaydedilemedi: {e}")

CONFIG = load_config()

# ----------------------------
# Utilities: email, capture
# ----------------------------

def timestamp():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def send_email(subject: str, body: str, attachments: list[Path] | None = None):
    if not CONFIG.get('email_enabled', False):
        logger.info('E-posta gönderimi kapalı (email_enabled=false).')
        return

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    mail_to = os.getenv('MAIL_TO') or smtp_user
    from_name = os.getenv('MAIL_FROM_NAME', 'SecureLock')

    if not smtp_host or not smtp_user or not smtp_password or not mail_to:
        logger.warning('SMTP yapılandırması eksik. E-posta gönderilmeyecek.')
        return

    msg = EmailMessage()
    from_addr = smtp_user
    msg['From'] = f"{from_name} <{from_addr}>"
    msg['To'] = mail_to
    msg['Subject'] = subject
    msg.set_content(body)

    if attachments and CONFIG.get('mail_attach_media', True):
        for path in attachments:
            try:
                data = path.read_bytes()
                msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=path.name)
            except Exception as e:
                logger.error(f"Ek eklenemedi: {path} -> {e}")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info('E-posta gönderildi.')
    except Exception as e:
        logger.error(f"E-posta gönderilemedi: {e}")


def capture_snapshot() -> Path | None:
    if not CONFIG.get('camera_enabled', False):
        logger.info('Kamera kapalı (camera_enabled=false).')
        return None
    try:
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cam.isOpened():
            logger.error('Kamera açılamadı.')
            return None
        time.sleep(0.2)  # kamera ısınsın
        ret, frame = cam.read()
        cam.release()
        if not ret:
            logger.error('Kameradan kare alınamadı.')
            return None
        out_path = CAPTURES_DIR / f"snapshot_{timestamp()}.jpg"
        cv2.imwrite(str(out_path), frame)
        logger.info(f"Anlık görüntü kaydedildi: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Kamera hatası: {e}")
        return None

def capture_screenshot() -> Path | None:
    """Capture full screen screenshot"""
    if not CONFIG.get('screenshot_enabled', True):
        logger.info('Ekran görüntüsü kapalı (screenshot_enabled=false).')
        return None
    try:
        # Take screenshot using PIL
        screenshot = ImageGrab.grab()
        out_path = CAPTURES_DIR / f"screenshot_{timestamp()}.png"
        screenshot.save(str(out_path), "PNG")
        logger.info(f"Ekran görüntüsü kaydedildi: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Ekran görüntüsü hatası: {e}")
        return None

def get_system_info() -> str:
    """Get system information"""
    try:
        import platform
        import psutil
        
        info = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "username": os.getenv('USERNAME', 'Unknown'),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return "\n".join([f"{k}: {v}" for k, v in info.items()])
    except Exception as e:
        logger.error(f"Sistem bilgisi alınamadı: {e}")
        return f"Hostname: {socket.gethostname()}\nError: {e}"


def capture_audio(seconds: int = 5) -> Path | None:
    if not CONFIG.get('audio_enabled', False):
        logger.info('Ses kaydı kapalı (audio_enabled=false).')
        return None
    try:
        samplerate = 44100
        channels = 1
        duration = max(1, int(CONFIG.get('audio_seconds', seconds)))
        logger.info(f"Ses kaydı başlıyor: {duration}s")
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='float32')
        sd.wait()
        data = np.squeeze(recording)
        out_path = CAPTURES_DIR / f"audio_{timestamp()}.wav"
        sf.write(str(out_path), data, samplerate)
        logger.info(f"Ses kaydı kaydedildi: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Ses kaydı hatası: {e}")
        return None


# ----------------------------
# Key mapping helper
# ----------------------------
_QT_KEY_MAP = {
    **{f"F{i}": getattr(Qt, f"Key_F{i}") for i in range(1, 25)},
    **{c: getattr(Qt, f"Key_{c}") for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')},
    **{str(i): getattr(Qt, f"Key_{i}") for i in range(0, 10)},
    "ESC": Qt.Key_Escape,
    "ENTER": Qt.Key_Return,
    "SPACE": Qt.Key_Space,
    "TAB": Qt.Key_Tab,
    "BACKSPACE": Qt.Key_Backspace,
}

def to_qt_key(key_name: str) -> int | None:
    if not key_name:
        return None
    name = key_name.strip().upper()
    return _QT_KEY_MAP.get(name)


# ----------------------------
# UI: Lock Window
# ----------------------------
class LockWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SecureLock')
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()

        self.unlocked = False
        self.last_capture_ts = 0.0
        self.cooldown = max(0, int(CONFIG.get('cooldown_seconds_between_captures', 30)))
        self.capture_lock = threading.Lock()
        self.unlock_mode = (CONFIG.get('unlock_mode') or 'key').lower()
        self.unlock_key_code = to_qt_key(CONFIG.get('unlock_key', 'F12'))
        self.safe_key_code = to_qt_key(CONFIG.get('safe_key', 'Y'))
        self.unlock_passcode = str(CONFIG.get('unlock_passcode', '123456'))
        
        # Security features
        self.security_enabled = CONFIG.get('security_mode_enabled', True)
        self.hook_installed = False
        
        # Install security hooks if enabled
        if self.security_enabled:
            if CONFIG.get('disable_task_manager', False):
                disable_task_manager()
            if CONFIG.get('block_system_keys', True):
                self.hook_installed = install_keyboard_hook()

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 2)
        self.label.setGraphicsEffect(shadow)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setMaxLength(64)
        self.pass_input.setPlaceholderText('Şifreyi girin ve Enter basın')
        self.pass_input.returnPressed.connect(self._on_pass_enter)
        self.pass_input.setVisible(self.unlock_mode == 'passcode')
        self.pass_input.setFont(QFont('Segoe UI', 18))
        
        # Enhanced styling for password input
        self.pass_input.setStyleSheet("""
            QLineEdit {
                padding: 15px 20px;
                border: 2px solid #444;
                border-radius: 10px;
                background-color: rgba(40, 40, 40, 0.9);
                color: white;
                font-size: 18px;
                margin: 10px;
                min-width: 300px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: rgba(50, 50, 50, 0.95);
            }
        """)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.pass_input)
        layout.addStretch()
        self.setLayout(layout)

        # Enhanced styling with gradient background
        theme = CONFIG.get('ui_theme', 'dark')
        if theme == 'dark':
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #0a0a0a, stop:1 #1a1a1a);
                }
                QLabel {
                    color: #ffffff;
                    background: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #f0f0f0, stop:1 #e0e0e0);
                }
                QLabel {
                    color: #000000;
                    background: transparent;
                }
            """)
        
        self._refresh_text()
        
        # Animation setup if enabled
        if CONFIG.get('show_animations', True):
            self._setup_animations()

        # Focus
        QTimer.singleShot(100, self._focus_self)

    def _focus_self(self):
        self.activateWindow()
        self.raise_()
        if self.unlock_mode == 'passcode':
            self.pass_input.setFocus()

    def _refresh_text(self):
        consent = ''
        if CONFIG.get('show_consent_banner', True):
            consent = ('\n\nBu cihaz kilitli ve izleniyor. Yanlış girişler kaydedilir ve ayarlar etkinse ' \
                       'kamera/ses kaydı alınabilir, e-posta gönderilebilir.')
        if self.unlock_mode == 'key':
            safe_name = CONFIG.get('safe_key', 'Y')
            keyname = (CONFIG.get('unlock_key') or '').strip()
            if self.unlock_key_code is None or keyname == '':
                self.label.setText(f"Cihaz kilitli.\n\n{safe_name} tuşu dışındaki tüm tuşlar izlemeyi tetikler.{consent}")
            else:
                self.label.setText(f"Cihaz kilitli.\n\nKilidi açmak için {keyname} tuşuna basın.{consent}")
        else:
            self.label.setText(f"Cihaz kilitli.\n\nKilidi açmak için şifreyi girin ve Enter'a basın.{consent}")

    # Window event handling
    def showEvent(self, event):
        """Ensure window stays on top and gets focus"""
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        # Force focus every 2 seconds to prevent focus loss
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self._ensure_focus)
        self.focus_timer.start(2000)
        
    def _ensure_focus(self):
        """Ensure window maintains focus"""
        if not self.unlocked:
            self.activateWindow()
            self.raise_()
            self.setFocus()

    # Wrong input handling
    def _trigger_wrong_input(self, reason: str):
        now = time.time()
        with self.capture_lock:
            if now - self.last_capture_ts < self.cooldown:
                return
            self.last_capture_ts = now
        logger.info(f"Yanlış giriş: {reason}")
        threading.Thread(target=self._capture_and_notify, args=(reason,), daemon=True).start()

    def _setup_animations(self):
        """Setup fade-in animation for the window"""
        self.setWindowOpacity(0.0)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()
        
    def _capture_and_notify(self, reason: str):
        host = socket.gethostname()
        when = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attachments: list[Path] = []
        
        # Capture screenshot first (usually more reliable than camera)
        screenshot = capture_screenshot()
        if screenshot:
            attachments.append(screenshot)
            
        img = capture_snapshot()
        if img:
            attachments.append(img)
            
        wav = capture_audio(CONFIG.get('audio_seconds', 5))
        if wav:
            attachments.append(wav)
            
        subject = f"[SecureLock] Yanlış giriş - {when}"
        
        # Enhanced email body with system info
        body = f"Makine: {host}\nZaman: {when}\nNeden: {reason}\n"
        body += f"Screenshot: {bool(screenshot)} | Kamera: {bool(img)} | Ses: {bool(wav)}\n"
        
        if CONFIG.get('include_system_info', True):
            body += f"\n--- Sistem Bilgileri ---\n{get_system_info()}\n"
            
        body += f"\nLog: {LOGS_DIR / 'activity.log'}\n"
        
        send_email(subject, body, attachments)

    # Key press
    def keyPressEvent(self, event):
        if self.unlock_mode == 'key':
            # Ignore key repeats to avoid spam
            if event.isAutoRepeat():
                event.accept()
                return
            # Safe key: do nothing
            if self.safe_key_code is not None and event.key() == self.safe_key_code:
                event.accept()
                return
            # Unlock key (if defined)
            if self.unlock_key_code is not None and event.key() == self.unlock_key_code:
                self._unlock()
                return
            # Anything else triggers capture
            self._trigger_wrong_input(f"Yanlış tuş: code={event.key()}")
        else:
            # passcode mode: do not trigger on every key, only on wrong submit
            if event.key() == Qt.Key_Escape:
                # Esc is not close; treat as wrong
                self._trigger_wrong_input("ESC")
        # do not propagate
        event.accept()

    def mousePressEvent(self, event):
        if self.unlock_mode == 'key' and CONFIG.get('mouse_triggers_enabled', True):
            self._trigger_wrong_input("Mouse tıklaması")
        event.accept()

    def mouseMoveEvent(self, event):
        if self.unlock_mode == 'key' and CONFIG.get('mouse_triggers_enabled', True):
            self._trigger_wrong_input("Mouse hareketi")
        event.accept()

    def _on_pass_enter(self):
        text = self.pass_input.text()
        if text == self.unlock_passcode:
            self._unlock()
        else:
            self.pass_input.clear()
            self._trigger_wrong_input("Yanlış şifre")

    def _unlock(self):
        self.unlocked = True
        logger.info('Kilit açıldı.')
        
        # Clean up security features
        if self.security_enabled:
            if CONFIG.get('disable_task_manager', False):
                enable_task_manager()
            if self.hook_installed:
                uninstall_keyboard_hook()
                
        self.close()
        
    def closeEvent(self, event):
        if not self.unlocked:
            event.ignore()
        else:
            # Cleanup on close
            if self.security_enabled and self.hook_installed:
                uninstall_keyboard_hook()
            super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = LockWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
