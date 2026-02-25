# GEMINI Context: Aerokou Drone Yer Kontrol İstasyonu (GCS)

Bu dosya, projenin mimarisi, teknolojileri ve geliştirme standartları hakkında temel bilgiler içerir.

## 🚀 Proje Genel Bakışı
Aerokou GCS, insansız hava araçlarının (İHA) MAVLink protokolü üzerinden gerçek zamanlı izlenmesi ve kontrol edilmesi için geliştirilmiş bir Yer Kontrol İstasyonu yazılımıdır. Sistem, düşük gecikmeli telemetri akışı ve modern bir kullanıcı arayüzü sunar.

### 🛠 Teknoloji Yığını
- **Backend:** Python 3.x, FastAPI, Pymavlink (MAVLink iletişimi için), Uvicorn.
- **Frontend:** React 19 (Vite), Tailwind CSS 4, Lucide-React (İkonlar), React-Leaflet (Harita).
- **İletişim:** REST API (Komutlar için) ve WebSocket (Gerçek zamanlı telemetri verileri için).

---

## 🏗 Mimari Yapı

### 📂 BACKEND (`/BACKEND`)
- **`main.py`:** Ana FastAPI sunucusu. Telemetri verilerini toplamak için arka planda bir thread çalıştırır ve WebSocket üzerinden istemcilere yayın yapar.
- **`pymavlink_custom/`:** Drone ile düşük seviyeli iletişimi (MAVLink) sağlayan özel sınıflar (`Vehicle` sınıfı vb.).
- **`config.json`:** Bağlantı portları (UDP/TCP), Drone ID'leri ve sistem parametrelerini içerir.

### 📂 FRONTEND (`/FRONTEND`)
- **`src/App.jsx`:** Ana dashboard bileşeni. Telemetri verilerini görselleştirir, harita takibini ve drone komutlarını yönetir.
- **Bileşenler:** HUD (üst bar), Telemetri Kartları, Harita (Leaflet), Kontrol Paneli ve Log Ekranı.

---

## 🏃 Çalıştırma Talimatları

### Backend'i Başlatma
```bash
cd BACKEND
# Sanal ortamı etkinleştirin
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

1.  **WebSocket Yönetimi:** Telemetri verileri `ConnectionManager` sınıfı üzerinden WebSocket ile anlık olarak frontend'e iletilir.
2.  **Hata Yönetimi:** Drone bağlantısı koptuğunda veya backend'e ulaşılamadığında kullanıcı arayüzünde görsel uyarılar gösterilmelidir.
3.  **UI/UX Standartları:** "Jarvis-style" karanlık tema (Siyah/Cyan/Kırmızı renk paleti) ve modern, teknolojik görünüm korunmalıdır.
4.  **Asenkron Yapı:** Backend tarafında FastAPI'nin asenkron özellikleri ve telemetri toplama için arka plan iş parçacıkları (threading) kullanılır.

---

## 📅 Yol Haritası (Güncel Durum)
- [x] FastAPI ve WebSocket entegrasyonu.
- [x] Temel MAVLink komutları (Arm, Takeoff, Land, Goto).
- [x] Harita entegrasyonu (Leaflet).
- [ ] Canlı video akışı (MJPEG) entegrasyonu.
- [ ] Çoklu drone desteğinin tam entegrasyonu.
- [ ] Arayüzün Türkçe optimizasyonu.

*Son Güncelleme: 25 Şubat 2026*
