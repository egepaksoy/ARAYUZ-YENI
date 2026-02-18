# Proje Yapısı - 25-26 ARAYÜZ

Bu klasör, İHA (Drone) kontrol ve telemetri sisteminin kullanıcı arayüzü bileşenlerini içerir. Sistem, modern bir web mimarisi olan **FastAPI + React** stack'ini kullanmaktadır.

## 📂 BACKEND
Drone ile haberleşen ve verileri ön yüze sunan sunucu tarafıdır.

*   **Teknoloji:** Python 3.x, FastAPI.
*   **main.py:** Projenin merkezi. Aşağıdaki temel görevleri yürütür:
    *   **REST API:** Ön yüzden gelen kalkış (takeoff), rota (goto) ve durum sorgulama isteklerini karşılar.
    *   **Telemetry Loop:** Arka planda 5Hz hızında çalışan bir thread ile drone verilerini (GPS, Alt, Mode, Arm) sürekli günceller.
    *   **Pymavlink Entegrasyonu:** `pymavlink_custom` kütüphanesi üzerinden drone donanımı ile konuşur.
*   **config.json:** Bağlantı portları ve drone ID'leri gibi yapılandırma verilerini içerir.
*   **apitest.py:** API uç noktalarını test etmek için kullanılan script.

## 📂 FRONTEND
Kullanıcının drone'u izlediği ve kontrol ettiği web arayüzüdür.

*   **Teknoloji:** React.js, Vite (Build Tool), Tailwind CSS (Styling).
*   **Yapı:**
    *   **src/:** Uygulamanın kaynak kodlarını ve React bileşenlerini içerir.
    *   **public/:** Statik dosyalar (ikonlar, resimler vb.).
*   **Özellikler:**
    *   FastAPI backend'inden gelen telemetri verilerini anlık olarak görselleştirir.
    *   Drone'a komut göndermek için kontrol butonları içerir.
    *   **Vite & Tailwind:** Modern ve hızlı bir geliştirme deneyimi sağlar.

---
*Hazırlayan: Rodrigo*
*Tarih: 12 Şubat 2026*
