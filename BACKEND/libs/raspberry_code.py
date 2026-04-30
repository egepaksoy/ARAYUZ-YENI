# Raspberry pi kamera ve gimbal kontrol kodu
import socket
import time
import threading

import io
import struct
from picamera2 import Picamera2


# --- Yapılandırma ---
PORT = 9999

stop_event = threading.Event()

def main(stop_event: threading.Event, host='0.0.0.0', port=9999):
    # Sunucu (Alıcı) soketini oluştur
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Gönderici {port} portunda bekleniyor (Picamera2 aktif)...")

    try:
        client_socket, addr = server_socket.accept()
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) # Nagle algoritmasını devre dışı bırak
        print(f"Alıcı bağlandı: {addr}")
        
        picam2 = Picamera2()
        # Kamera ayarları
        config = picam2.create_video_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        
        # Kameranın ısınması için kısa bir bekleme
        time.sleep(2)

        stream = io.BytesIO()

        # Sürekli olarak JPEG formatında yakala ve gönder
        while not stop_event.is_set():
            stream.seek(0)
            stream.truncate()
            
            # Görüntüyü stream'e JPEG olarak yakala
            picam2.capture_file(stream, format='jpeg')
            
            # Verinin boyutunu al
            image_len = stream.tell()
            if image_len > 0:
                # Önce boyutu (unsigned long), sonra veriyi gönder
                client_socket.sendall(struct.pack(">L", image_len))
                
                stream.seek(0)
                client_socket.sendall(stream.read())

    except Exception as e:
        print(f"Kamera/Gönderici Hatası: {e}")
    except KeyboardInterrupt:
        print("Koddan cikildi")
    finally:
        if 'picam2' in locals():
            picam2.stop()
        if 'client_socket' in locals():
            client_socket.close()
        server_socket.close()
        print("Kamera ve bağlantı kapatıldı.")


if __name__ == "__main__":
    main(stop_event=stop_event, port=PORT)
