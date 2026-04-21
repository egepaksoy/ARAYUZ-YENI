import socket
import struct
import math
import time
import cv2
from picamera2 import Picamera2

# ==========================================
# DİKKAT: BİLGİSAYARININ (BACKEND) IP ADRESİNİ YAZ
# ==========================================
UDP_IP = "192.168.31.172"  
UDP_PORT = 5000           
MAX_IMAGE_DGRAM = 60000   

def start_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Görüntü {UDP_IP}:{UDP_PORT} adresine UDP üzerinden gönderiliyor...")

    # Picamera2'yi başlat
    picam2 = Picamera2()
    
    # Kamerayı VİDEO modunda başlatıyoruz. 
    # format="BGR888" çok önemli: OpenCV renkleri BGR okur. RGB yaparsak renkler ters (mavi) olur.
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()

    # Kameranın açılması, ışık ve renk ayarlarının (AE/AWB) oturması için 2 saniye bekle
    time.sleep(2)

    frame_number = 0

    try:
        while True:
            # Kameranın sürekli akan video tamponundan (buffer) en son kareyi alıyoruz.
            # Bu sayede renkler ASLA solmaz, canlı ve gerçekçi kalır.
            frame = picam2.capture_array("main")

            # Görüntüyü hızlıca JPEG olarak sıkıştır (%80 kalite bant genişliğini korur)
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue
                
            data = buffer.tobytes()
            size = len(data)
            
            # Görüntüyü UDP sınırına göre parçalara böl
            num_of_segments = math.ceil(size / MAX_IMAGE_DGRAM)
            array_pos_start = 0
            
            while num_of_segments:
                array_pos_end = min(size, array_pos_start + MAX_IMAGE_DGRAM)
                chunk = data[array_pos_start:array_pos_end]
                
                # Çerçeve numarasını (4 bayt) parçanın başına ekle
                packet = struct.pack('<L', frame_number) + chunk
                sock.sendto(packet, (UDP_IP, UDP_PORT))
                
                array_pos_start = array_pos_end
                num_of_segments -= 1
                
            # Parçaların bittiğini bildiren END etiketini gönder
            end_packet = struct.pack('<L', frame_number) + b'END'
            sock.sendto(end_packet, (UDP_IP, UDP_PORT))
            
            frame_number += 1
            
            # Sistemi ve ağı yormamak için çok kısa bekleme
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")
    finally:
        picam2.stop() # Kamerayı düzgünce kapat
        sock.close()
        print("Kamera ve bağlantı kapatıldı.")

if __name__ == "__main__":
    start_sender()