#!/usr/bin/env python3
"""
SecureLock Configuration Manager
Kolay config yönetimi için yardımcı script
"""

import json
import sys
from pathlib import Path

# Config dosyası yolu
CONFIG_FILE = Path(__file__).parent / 'config.json'

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

def load_config():
    """Mevcut config'i yükle"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Config yüklenemedi: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Config'i kaydet"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Config kaydedildi: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Config kaydedilemedi: {e}")
        return False

def show_config():
    """Mevcut config'i göster"""
    config = load_config()
    print("=== Mevcut Konfigürasyon ===")
    for key, value in config.items():
        print(f"{key:30} = {value}")

def reset_config():
    """Config'i varsayılanlara döndür"""
    if save_config(DEFAULT_CONFIG):
        print("Config varsayılan değerlere döndürüldü.")

def set_unlock_mode():
    """Kilit açma modunu ayarla"""
    config = load_config()
    print("Kilit açma modu:")
    print("1. Tek tuş (key)")
    print("2. Şifre (passcode)")
    
    choice = input("Seçiminiz (1/2): ").strip()
    if choice == "1":
        config['unlock_mode'] = 'key'
        key = input("Kilit açma tuşu (örn: F12, ENTER, ESC): ").strip()
        config['unlock_key'] = key
        print(f"Kilit açma modu: Tek tuş ({key})")
    elif choice == "2":
        config['unlock_mode'] = 'passcode'
        passcode = input("Yeni şifre (en az 4 karakter): ").strip()
        if len(passcode) >= 4:
            config['unlock_passcode'] = passcode
            print("Kilit açma modu: Şifre")
        else:
            print("Şifre çok kısa!")
            return
    else:
        print("Geçersiz seçim!")
        return
    
    save_config(config)

def toggle_features():
    """Özellikleri aç/kapat"""
    config = load_config()
    
    features = {
        '1': ('camera_enabled', 'Kamera'),
        '2': ('audio_enabled', 'Ses kaydı'),
        '3': ('screenshot_enabled', 'Ekran görüntüsü'),
        '4': ('email_enabled', 'E-posta bildirimi'),
        '5': ('security_mode_enabled', 'Güvenlik modu'),
        '6': ('block_system_keys', 'Sistem tuşlarını engelle'),
        '7': ('show_animations', 'Animasyonlar'),
        '8': ('mouse_triggers_enabled', 'Mouse tetikleyicileri')
    }
    
    print("=== Özellik Ayarları ===")
    for key, (config_key, name) in features.items():
        status = "AÇIK" if config.get(config_key, False) else "KAPALI"
        print(f"{key}. {name:25} [{status}]")
    
    choice = input("Değiştirmek istediğiniz özellik (1-8): ").strip()
    if choice in features:
        config_key, name = features[choice]
        config[config_key] = not config.get(config_key, False)
        status = "AÇIK" if config[config_key] else "KAPALI"
        print(f"{name} -> {status}")
        save_config(config)
    else:
        print("Geçersiz seçim!")

def main():
    """Ana menü"""
    while True:
        print("\n=== SecureLock Config Yöneticisi ===")
        print("1. Mevcut ayarları göster")
        print("2. Kilit açma modunu ayarla")
        print("3. Özellikleri aç/kapat")
        print("4. Ayarları varsayılana döndür")
        print("5. Çıkış")
        
        choice = input("Seçiminiz (1-5): ").strip()
        
        if choice == "1":
            show_config()
        elif choice == "2":
            set_unlock_mode()
        elif choice == "3":
            toggle_features()
        elif choice == "4":
            confirm = input("Tüm ayarlar silinecek! Emin misiniz? (y/N): ").strip().lower()
            if confirm == 'y':
                reset_config()
        elif choice == "5":
            print("Çıkılıyor...")
            break
        else:
            print("Geçersiz seçim!")

if __name__ == "__main__":
    main()
