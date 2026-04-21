import sys
import cv2
import socket
import numpy as np
import struct
import time

if len(sys.argv) != 3:
    print("Kod kullanımı python detect.py <ip_adresi> <port numarası>")
    exit()

# Kullanıcıdan IP adresi ve port numarasını komut satırından al
UDP_IP = sys.argv[1]  # Alıcı bilgisayarın IP adresi
UDP_PORT = int(sys.argv[2])  # Alıcı bilgisayarın port numarası
BUFFER_SIZE = 60000  # UDP tampon boyutu, 64 KB

try:
    # UDP soketi oluştur ve belirtilen IP ve portta dinlemeye başla
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    buffer = b''  # Gelen veri parçalarını depolamak için tampon
    current_frame = -1  # Geçerli çerçeve numarasını takip etmek için sayaç

    total_frame = 0

    frame_time = time.time()
    fps = 0
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)  # Maksimum UDP paket boyutu kadar veri al
        
        # Çerçeve numarasını çöz
        frame_number = struct.unpack('<L', data[:4])[0]
        packet_data = data[4:]

        if frame_number != current_frame:
            if buffer:
                # Görüntüyü verinin tamamı alındığında oluştur
                npdata = np.frombuffer(buffer, dtype=np.uint8)
                frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    if time.time() - frame_time >= 1:
                        fps = total_frame / (time.time() - frame_time)
                        total_frame = 0
                        frame_time = time.time()

                    cv2.putText(frame, f"{fps:.1f}", (0, 25), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    cv2.imshow('Live image', frame)  # Görüntüyü göster
                
                buffer = b''  # Yeni görüntü için tamponu sıfırla

            current_frame = frame_number  # Geçerli çerçeve numarasını güncelle
            total_frame += 1
        
        if packet_data == b'END':
            # Son paket işareti, çerçevenin sonu
            continue
        
        buffer += packet_data  # Gelen veri parçasını tampona ekle

        # Çıkış için 'q' tuşuna basılması beklenir
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
except Exception as e:
    print("Bir hata oluştu:", e)

except KeyboardInterrupt:
    print("Ctrl+C ile çıkıldı.")

except:
    print("Beklenmeyen bir hata oluştu.")

finally:
    print("Program sonlandırıldı.")
    cv2.destroyAllWindows()  # Tüm OpenCV pencerelerini kapat
    sock.close()  # Soketi kapat