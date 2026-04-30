# Goruntu isleme kutuphanesi
import socket, struct
import time
import threading
import numpy as np
import cv2
from ultralytics import YOLO

class Handler:
    def __init__(self, stop_event: threading.Event=None, window_name: str="Goruntu", middle_range: int=0.4):
        self.model = None
        self.proccessing = False

        if stop_event is None:
            self.stop_event = threading.Event()
        else:
            self.stop_event = stop_event

        self.screen_res = None
        self.screen_center = None
        
        self.showing_image = True

        self.middle_range = middle_range

        self.window_name = window_name

        self.ters = True

        self.conf = 0.9

        self.video_started = False

        self.detected_obj = {
            "cls": None,
            "pos": None,
            "dist": None,
            "lt": None,
            "screen_res": None
        }
        self.object_lock = threading.Lock()

        # Arayüze canlı yayın icin
        self.output_frame = None
        self.output_lock = threading.Lock()
    
    def get_detected_obj(self):
        """Algılanan objeleri dict olarak dondurur
        
        Keyword arguments:
        Return: cls, pos, dist, lt, screen_res
        """
        with self.object_lock:
            detected_obj = self.detected_obj
        
        return detected_obj

    def local_camera(self, camera_path: int=0):
        cap = cv2.VideoCapture(camera_path)
        class_name = None

        if not cap.isOpened():
            print(f"Dahili kamera {camera_path} açılamadı")
            return
    
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        try:
            while not self.stop_event.is_set():
                _, frame = cap.read()

                if frame is not None:
                    if self.ters:
                        frame = cv2.flip(frame, -1)
                    self.screen_res = (int(frame.shape[:2][1]), int(frame.shape[:2][0]))
                    self.screen_center = (self.screen_res[0] / 2, self.screen_res[1] / 2)

                    if self.proccessing and self.model is not None:
                        results = self.model(frame, verbose=False, device="cpu")
                        class_name = None

                        for r in results:
                            boxes = r.boxes
                            for box in boxes:
                                if box.conf[0] < self.conf:
                                    continue
                                # Sınırlayıcı kutu koordinatlarını al
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                obj_center = (float((x1+x2) / 2), float((y1+y2) / 2))

                                # Sınıf ve güven skorunu al
                                model_cls = int(box.cls[0].item())
                                conf = box.conf[0].item()

                                # Sınıf adını al
                                class_name = self.model.names[model_cls]

                                # Nesneyi çerçeve içine al ve etiketle
                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                                cv2.putText(frame, f"{class_name} {conf:.2f}", (int(x1), int(y1 - 10)), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    if self.object_lock != None and self.detected_obj != None:
                        if class_name is None:
                            with self.object_lock:
                                self.detected_obj["cls"] = None
                                self.detected_obj["pos"] = None
                                self.detected_obj["dist"] = None
                                self.detected_obj["screen_res"] = self.screen_res

                        else:
                            with self.object_lock:
                                self.detected_obj["cls"] = class_name
                                self.detected_obj["pos"] = obj_center
                                self.detected_obj["dist"] = self.get_distance(obj_center)
                                self.detected_obj["lt"] = time.time()
                                self.detected_obj["screen_res"] = self.screen_res
                    # self.visualize_box(frame)
                    
                    with self.output_lock:
                        ret, buffer = cv2.imencode('.jpg', frame)
                        if ret:
                            self.output_frame = buffer.tobytes()

                    if self.showing_image:
                        cv2.imshow(self.window_name, frame)
                    
                    self.video_started = True

                cv2.waitKey(1)

        finally:
            # Kamera ve pencereleri güvenli bir şekilde kapat
            cap.release()
            cv2.destroyAllWindows()
            print(f"[ImageProcessor] Kamera {camera_path} serbest bırakıldı.")

    def udp_camera(self, rpi_ip: str="172.16.13.31", port: int=9999):
        class_name = None
        # TCP İstemci soketi oluştur
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) # Nagle algoritmasını devre dışı bırak
        
        print(f"{rpi_ip}:{port} adresine bağlanılmaya çalışılıyor...")
        client_socket.connect((rpi_ip, port))
        print("Bağlantı başarılı!")

        self.latest_frame = None
        self.frame_lock = threading.Lock()

        def frame_receiver():
            data = b""
            payload_size = struct.calcsize(">L")
            try:
                while not self.stop_event.is_set():
                    # Önce paketin boyutunu (4 byte) oku
                    while len(data) < payload_size:
                        packet = client_socket.recv(65536)
                        if not packet: return
                        data += packet
                    
                    packed_msg_size = data[:payload_size]
                    data = data[payload_size:]
                    msg_size = struct.unpack(">L", packed_msg_size)[0]

                    # Belirlenen boyutta veriyi çek (asıl görüntü verisi)
                    while len(data) < msg_size:
                        packet = client_socket.recv(65536)
                        if not packet: return
                        data += packet
                    
                    frame_data = data[:msg_size]
                    data = data[msg_size:]

                    # Byte verisini JPEG'den görüntüye dönüştür
                    frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        with self.frame_lock:
                            self.latest_frame = frame
                
            except Exception as e:
                print(f"Receiver Thread Hatası: {e}")

        # Görüntü alım thread'ini başlat
        receiver_thread = threading.Thread(target=frame_receiver, daemon=True)
        receiver_thread.start()

        try:
            while not self.stop_event.is_set():
                # En güncel kareyi al
                with self.frame_lock:
                    frame = self.latest_frame
                    self.latest_frame = None # Kareyi "tüket"
                
                if frame is None:
                    time.sleep(0.01) # Yeni kare için çok kısa bekleme
                    continue

                # Goruntu isleme kismi
                if self.ters:
                    frame = cv2.flip(frame, -1)
                self.screen_res = (int(frame.shape[:2][1]), int(frame.shape[:2][0]))
                self.screen_center = (self.screen_res[0] / 2, self.screen_res[1] / 2)

                if self.proccessing and self.model is not None:
                    results = self.model(frame, verbose=False, device="cpu")
                    class_name = None

                    for r in results:
                        boxes = r.boxes
                        for box in boxes:
                            if box.conf[0] < self.conf:
                                continue
                            # Sınırlayıcı kutu koordinatlarını al
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            obj_center = (float((x1+x2) / 2), float((y1+y2) / 2))

                            # Sınıf ve güven skorunu al
                            model_cls = int(box.cls[0].item())
                            conf = box.conf[0].item()

                            # Sınıf adını al
                            class_name = self.model.names[model_cls]

                            # Nesneyi çerçeve içine al ve etiketle
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            cv2.putText(frame, f"{class_name} {conf:.2f}", (int(x1), int(y1 - 10)), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                if self.object_lock != None and self.detected_obj != None:
                    if class_name is None:
                        with self.object_lock:
                            self.detected_obj["cls"] = None
                            self.detected_obj["pos"] = None
                            self.detected_obj["dist"] = None
                            self.detected_obj["screen_res"] = self.screen_res

                    else:
                        with self.object_lock:
                            self.detected_obj["cls"] = class_name
                            self.detected_obj["pos"] = obj_center
                            self.detected_obj["dist"] = self.get_distance(obj_center)
                            self.detected_obj["lt"] = time.time()
                            self.detected_obj["screen_res"] = self.screen_res

                with self.output_lock:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        self.output_frame = buffer.tobytes()

                if self.showing_image:
                    cv2.imshow(self.window_name, frame)
                
                self.video_started = True

                # Çıkış için 'q' tuşuna basılması beklenir
                cv2.waitKey(1)

        except Exception as e:
            print(f"Hata: {e}")
        finally:
            client_socket.close()
            cv2.destroyAllWindows()

    def visualize_box(self, frame):
        x1 = (self.screen_res[0] - (self.screen_res[0] * self.middle_range)) / 2
        x2 = self.screen_res[0] - x1
        y1 = (self.screen_res[1] - (self.screen_res[1] * self.middle_range)) / 2
        y2 = self.screen_res[1] - y1

        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 1)
    
    def get_distance(self, obj_center):
        return float(obj_center[0] - self.screen_center[0]), float(obj_center[1] - self.screen_center[1])
    
    def start_proccessing(self, model_path, conf: float=0.8):
        if self.model == None:
            self.model = YOLO(model_path)
            print("model yuklendi")

        self.conf = conf
        self.proccessing = True
