# SecureLock (Enhanced Security Kiosk)

Gelişmiş güvenlik özellikleri ile donatılmış, açık uyarı gösteren ve kullanıcı açıkça etkinleştirirse yanlış girişlerde anlık görüntü (kamera), ekran görüntüsü ve kısa ses kaydı alabilen, e-posta ile bildirim gönderebilen Windows kilit ekranı uygulaması.

Önemli: Bu yazılım gizli izleme amaçlı değildir. Uygulama tam ekranda görünür uyarı gösterir. Kamera/ses kaydı ve e-posta gönderimi varsayılan olarak kapalıdır ve yalnızca kullanıcı açıkça etkinleştirirse çalışır. Yerel yasa ve yönetmeliklere uymak kullanıcı sorumluluğundadır.

## ✨ Özellikler

### 🔒 Güvenlik
- Tam ekran, en üstte kalan kilit ekranı (kiosk benzeri)
- Sistem tuşlarını engelleme (Alt+Tab, Win+L, Ctrl+Alt+Del)
- Task Manager'ı devre dışı bırakma (isteğe bağlı)
- Düşük seviye keyboard hook ile gelişmiş koruma
- "Tek tuş" veya "şifre" ile açma (config.json ile seçilir)

### 📹 Medya Yakalama
- Kamera anlık görüntüsü alma (OpenCV)
- Ekran görüntüsü alma (otomatik etkin)
- Kısa ses kaydı (sounddevice + soundfile)
- Sistem bilgileri toplama (CPU, RAM, kullanıcı bilgileri)

### 🎨 Gelişmiş UI/UX
- Modern gradient arkaplan
- Animasyonlu geçişler
- Gölge efektleri
- Karanlık/Açık tema desteği
- Responsive tasarım

### 📧 Bildirim Sistemi
- E-posta ile anlık bildirim
- Medya dosyalarını ek olarak gönderme
- Detaylı sistem bilgileri
- SMTP desteği (Gmail, Outlook, vb.)

### 📊 Gelişmiş Loglama
- Rotating log dosyaları (10MB limit, 5 yedek)
- Detaylı zaman damgaları
- Farklı log seviyeleri
- Hata takibi ve debug bilgileri

### ⚙️ Kolay Konfigürasyon
- JSON tabanlı ayar sistemi
- Config doğrulama ve sanitizasyon
- Varsayılan ayar oluşturma
- Grafik config yöneticisi (`config_manager.py`)

### 🛡️ Güvenli Varsayılanlar
- Tüm medya yakalama kapalı
- E-posta bildirimi kapalı
- Gizlilik odaklı varsayılan ayarlar

## 🚀 Kurulum

### Gereksinimler
- Python 3.10+ (Windows önerilir)
- Windows 10/11 (sistem hook'ları için)
- Yönetici hakları (güvenlik özellikleri için)

### Adım Adım Kurulum

1) **Bağımlılıkları kurun:**
```bash
pip install -r requirements.txt
```

2) **E-posta ayarlarını yapın (isteğe bağlı):**
```bash
# env.example dosyasını .env olarak kopyalayın
copy env.example .env
# .env dosyasını düzenleyip SMTP bilgilerinizi girin
```

3) **Konfigürasyonu ayarlayın:**
```bash
# Kolay config için yönetici scripti kullanın
python config_manager.py
```

### 🎯 Hızlı Başlangıç
```bash
# Varsayılan ayarlarla çalıştır (güvenli mod)
python src/main.py

# Config yöneticisi ile ayarları değiştir
python config_manager.py
```

## Çalıştırma

```bash
python src/main.py
```

İlk açılışta tam ekran uyarı görüntülenir. `unlock_mode` değerine göre:
- `key`: Belirlediğiniz tek tuşa basınca kilit açılır. Başka bir tuş/klik/mouse hareketi yanlış giriş sayılır.
- `passcode`: Parola alanına doğru şifreyi girip Enter'a basın. Yanlış şifre denemesi olay olarak kaydedilir.

Olaylarda, medya/e-posta özellikleri config ile açık ise tetiklenir.

## Paketleme (Windows .exe)

PyInstaller ile tek dosya exe üretebilirsiniz:

```bash
pip install pyinstaller
pyinstaller --noconsole --name SecureLock --onefile src/main.py
```

Notlar:
- `config.json` ve `.env` dosyasını exe ile aynı klasöre koyun.
- Kamerası/mikrofonu olmayan makinede medya yakalama başarısız olabilir; uygulama hatayı loglar ve çalışmaya devam eder.

## Güvenlik ve Kısıtlar

- Bu uygulama bir OS-kilit (Win+L) yerine görsel/uygulama tabanlı bir kilittir. Sistem kısayolları (Ctrl+Alt+Del vb.) tamamen engellenemez.
- Yalnızca yetkili kullanım için. Uygulamayı kullanmadan önce tüm ilgili kişilere açık uyarı gösterir.

## Yapılandırma (config.json)

- `unlock_mode`: `"key"` veya `"passcode"`
- `unlock_key`: Örn. `"F12"`
- `unlock_passcode`: Örn. `"123456"`
- `camera_enabled`: true/false
- `audio_enabled`: true/false
- `audio_seconds`: Örn. 5
- `email_enabled`: true/false
- `mail_attach_media`: true/false
- `cooldown_seconds_between_captures`: aynı olayların spam olmaması için bekleme süresi

## Lisans

MIT Lisansı. Ayrıntılar için `LICENSE` dosyasına bakın.
