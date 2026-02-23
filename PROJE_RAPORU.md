# Aerokou Drone Yer Kontrol İstasyonu (GCS) Proje Raporu

## 1. Proje Genel Bakışı
Bu proje, insansız hava araçlarının (İHA) gerçek zamanlı izlenmesi ve kontrol edilmesi amacıyla geliştirilmiş bir Yer Kontrol İstasyonu (GCS) yazılımıdır. Sistem, modern web teknolojileri ile geliştirilmiş bir ön yüz (Frontend) ve İHA ile iletişimi sağlayan bir arka yüzden (Backend) oluşmaktadır.

---

## 2. Teknik Mimari

### 2.1 Arka Yüz (Backend)
- **Teknoloji:** Python, FastAPI
- **İletişim Protokolü:** MAVLink (pymavlink kütüphanesi üzerinden)
- **Temel Dosyalar:**
  - `main.py`: Ana API sunucusu. Telemetri verilerini toplar ve komutları İHA'ya iletir.
  - `config.json`: Bağlantı portları ve İHA ID'si gibi yapılandırma ayarlarını içerir.
  - `pymavlink_custom/`: MAVLink protokolü üzerinden İHA ile düşük seviyeli iletişimi sağlayan özel sınıflar.

**Öne Çıkan Özellikler:**
- **Gerçek Zamanlı Telemetri:** Arka planda çalışan bir `telemetry_update_loop` (iş parçacığı/thread), İHA'dan sürekli olarak konum (enlem, boylam, irtifa), mod, silahlanma (arm) durumu ve yön (heading) bilgilerini çeker.
- **API Uç Noktaları:** Ön yüzün drone'a komut göndermesi için `/command/arm`, `/command/start-mission`, `/command/failsafe-mission` gibi REST API uç noktaları sağlar.
- **Çoklu İş Parçacığı Yönetimi:** Telemetri güncellemeleri ve drone komutları, ana sunucuyu engellememek için ayrı thread'lerde yönetilir.

### 2.2 Ön Yüz (Frontend)
- **Teknoloji:** React, Vite, Tailwind CSS, Lucide-React (İkonlar)
- **Dosya Yapısı:** `App.jsx`, `App.css`, `main.jsx`

**Öne Çıkan Özellikler:**
- **HUD (Head-Up Display):** Pilotun drone durumunu (SİLAHLI/GÜVENLİ) ve bağlantı durumunu anında görebileceği üst bilgi çubuğu.
- **Telemetri Paneli:** İrtifa, dikey hız, yön ve GPS koordinatlarını dinamik olarak gösteren kartlar.
- **Kontrol Merkezi:**
  - **Primary Controls:** Sistemi silahlandırma (ARM) ve devreden çıkarma (DISARM) butonları.
  - **Flight Actions:** Görevi başlatma (START-MISSION) ve acil durum iniş/eve dönüş (FAILSAFE) butonları.
- **Görev Logları:** Sistemden gelen başarı veya hata mesajlarını zaman damgasıyla listeleyen terminal ekranı.
- **Video Yayını Arayüzü:** İHA'dan gelecek video yayını için hazırlanmış, tarama çizgisi efektli HUD alanı.

---

## 3. Çalışma Mantığı
1. **Bağlantı:** Backend başlatıldığında `config.json` dosyasındaki porta bağlanmaya çalışır.
2. **Telemetri Akışı:** Bağlantı sağlandığında, saniyede 5 kez (5Hz) güncellenen bir döngü ile İHA verileri çekilir ve global bir değişkende tutulur.
3. **Ön Yüz Güncelleme:** React uygulaması, 1.5 saniyede bir `/telemetry` uç noktasını sorgulayarak güncel verileri ekrana yansıtır.
4. **Komut Gönderimi:** Kullanıcı arayüzdeki bir butona bastığında, ilgili API uç noktasına bir POST isteği gönderilir ve Backend bu komutu MAVLink üzerinden İHA'ya iletir.

---

## 4. Sonuç
Bu sistem, kullanıcı dostu ve modern bir arayüz ile karmaşık drone operasyonlarını yönetmeyi kolaylaştırmaktadır. Modüler yapısı sayesinde yeni özellikler (yol noktası ekleme, gelişmiş otonom görevler vb.) kolayca entegre edilebilir.
