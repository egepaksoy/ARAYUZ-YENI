# GEMINI Context: Aerokou Drone Yer Kontrol İstasyonu (GCS)

Bu dosya, projenin mimarisi, teknolojileri ve geliştirme standartları hakkında temel bilgiler içerir.

## 🚀 Proje Genel Bakışı
Aerokou GCS, insansız hava araçlarının (İHA) MAVLink protokolü üzerinden gerçek zamanlı izlenmesi ve kontrol edilmesi için geliştirilmiş bir Yer Kontrol İstasyonu yazılımıdır. Sistem, düşük gecikmeli telemetri akışı ve modern bir kullanıcı arayüzü sunar.

### 🛠 Teknoloji Yığını
- **Backend:** Python 3.x, FastAPI, Pymavlink (MAVLink iletişimi için).
- **Frontend:** React (Vite), Tailwind CSS, Lucide-React (İkonlar), Leaflet (Harita).
- **İletişim:** REST API (Komutlar için) ve HTTP Polling (Telemetri için - WebSocket planlanıyor).

---

## 🏗 Mimari Yapı

### 📂 BACKEND (`/BACKEND`)
- **`main.py`:** Ana uygulama sunucusu. Telemetri verilerini toplamak için arka planda bir thread çalıştırır ve frontend'den gelen komutları karşılar.
- **`pymavlink_custom/`:** MAVLink paketlerini işleyen ve drone ile düşük seviyeli iletişimi sağlayan özel sınıflar.
- **`config.json`:** Bağlantı portları (UDP/TCP), Drone ID'leri ve görev parametrelerini içerir.

### 📂 FRONTEND (`/FRONTEND`)
- **`src/App.jsx`:** Ana dashboard bileşeni. Telemetri verilerini görselleştirir, video yayınını (hazırlık aşamasında) ve harita takibini yönetir.
- **Bileşenler:** HUD (üst bar), Telemetri Kartları, Harita (Leaflet), Görev Logları ve Kontrol Paneli.

---

## 🏃 Çalıştırma Talimatları

### Backend'i Başlatma
```bash
cd BACKEND
# Sanal ortamı etkinleştirin (isteğe bağlı)
python main.py
```
*Backend varsayılan olarak `http://localhost:8000` adresinde çalışır.*

### Frontend'i Başlatma
```bash
cd FRONTEND
npm install
npm run dev
```
*Frontend varsayılan olarak `http://localhost:5173` adresinde çalışır.*

---

## 📝 Geliştirme Konvansiyonları

1.  **Telemetri Akışı:** Telemetri verileri backend'de `state_lock` ile korunur. Yeni bir veri eklenirken veya okunurken bu lock kullanılmalıdır.
2.  **Hata Yönetimi:** Drone bağlantısı koptuğunda frontend'de "Bağlantı Bekleniyor" uyarısı gösterilir. Backend'deki komutlar drone bağlantısını kontrol etmeden işlem yapmamalıdır.
3.  **UI/UX Standartları:** "Jarvis-style" karanlık tema (Siyah/Cyan/Kırmızı renk paleti) korunmalıdır.
4.  **Görev Kontrolü:** `stop_event` nesnesi acil durum durdurmaları (Failsafe) için kullanılır. Yeni bir görev başlatılmadan önce bu event `clear()` edilmelidir.

---

## 📅 Yol Haritası (TODO)
- [ ] Telemetri için WebSocket entegrasyonu.
- [ ] Canlı video akışı (MJPEG) entegrasyonu.
- [ ] Çoklu drone desteğinin arayüze tam entegrasyonu.
- [ ] Harita üzerinde waypoint (rota noktası) ekleme özelliği.

*Son Güncelleme: 25 Şubat 2026*
