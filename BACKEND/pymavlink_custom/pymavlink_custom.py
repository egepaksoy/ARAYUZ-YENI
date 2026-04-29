from pymavlink import mavutil, mavwp # MAVLink protokolü ve görev (waypoint) yönetimi için kütüphaneler
import serial.tools.list_ports # Bilgisayara bağlı seri portları (USB/COM) listelemek için
import time # Zaman tabanlı işlemler ve beklemeler için
import math # Matematiksel hesaplamalar (derece/radyan dönüşümü vb.) için
import threading # Arka planda eşzamanlı (multithreading) işlemler yürütmek için
from geopy.distance import geodesic # İki koordinat arasındaki mesafeyi (metre) hesaplamak için

# TODO: terminale yazdırılan mesajlari renkli yazdıran bir fonksiyon yap. ayrıca bu renk temasini arayüzdeki terminalde de birebir göster
class Vehicle:
    def __init__(self, address: str = None, stop_event: threading.Event = None, baud: int = 57600, autoreconnect: bool = True, on_flight: bool = True):
        """
        Gelişmiş Pymavlink Araç Sınıfı.
        Bu sınıf, drone ile iletişimi arka planda sürekli dinleyerek (listener) yönetir.
        """

        try:
            # Bağlantı adresini kontrol et (Eğer boşsa uygun portu otomatik bulur)
            address = self._check_address(address)
            print(f"[Vehicle]>> Bağlantı adresi: {address}")
            
            # MAVLink bağlantısını kur
            self.vehicle = mavutil.mavlink_connection(device=address, baud=baud, autoreconnect=autoreconnect)
            
            # İlk 'Heartbeat' mesajını bekle (Drone'un orada olduğunu doğrular)
            self.vehicle.wait_heartbeat()
            print("[Vehicle]>> Bağlantı başarılı.")

            # Durum Yönetimi Değişkenleri
            self.stop_event = stop_event if stop_event else threading.Event() # Sistemi durdurmak için sinyal
            self.state_lock = threading.Lock() # Çoklu drone verilerine güvenli erişim (Race condition engelleme)
            
            # Tüm drone'ların verilerini tutan merkezi hafıza (Cache)
            # Yapı: {drone_id: {"lat": 0.0, "lon": 0.0, ...}}
            self._drones_state = {}
            self.TAKEOFF_POS = {} # Drone'ların kalkış yaptığı koordinatları saklar
            self.DEG = 0.00001172485 # Yaklaşık 1 metrenin enlem/boylam derecesi karşılığı

            # Mesaj Dinleyici Thread'i (Arka planda sürekli çalışır)
            if on_flight:
                # Drone'dan belirli mesajları belirli aralıklarla göndermesini iste (Hızlandırma)
                self._request_initial_telemetry()

                # Mesajlarin dronelara ulasmasi icin 2sn bekleme
                start_time = time.time()            
                while time.time() - start_time <= 2:
                    time.sleep(0.2)

                self._listener_thread = threading.Thread(target=self._message_listener_loop, daemon=True)
                self._listener_thread.start() # Dinleme işlemini başlat

                # Varsayılan Drone id
                self.drone_id = list(self.get_all_drone_ids())[0] if len(self.get_all_drone_ids()) else 0

                # Waypoint (Görev) Yükleyicisi
                self.wp = mavwp.MAVWPLoader()

            print("[Vehicle]>> Uçuş öncesi veriler çekilmesi için 5sn bekleniyor")
            start_time = time.time()            
            while time.time() - start_time <= 5:
                time.sleep(0.2)

        except Exception as e:
            print(f"[Vehicle] Kritik Hata (init): {e}")
            raise

    # --- İç Fonksiyonlar (Özel İşlemler) ---

    def _check_address(self, address: str):
        """Bağlantı adresini doğrular veya otomatik port taraması yapar."""

        try:
            if address is None:
                ports = serial.tools.list_ports.comports()
                if not ports:
                    Exception("Hicbir baglanti yolu bulunamadi")
                return ports[0].device # İlk bulduğu portu kullan
            return address
        except Exception as e:
            print(e)

    def _message_listener_loop(self):
        """Tüm gelen MAVLink paketlerini yakalayıp hafızayı güncelleyen ana döngü."""
        while not self.stop_event.is_set():
            try:
                # Bloklamadan mesaj bekle (0.1sn timeout ile işlemciyi yormaz)
                msg = self.vehicle.recv_match(blocking=True, timeout=0.1)
                if not msg:
                    continue # Mesaj yoksa döngüye devam et

                # Mesajın geldiği drone ID'sini al
                drone_id = msg.get_srcSystem()
                if drone_id == 0 or drone_id == 255: # Yer istasyonu mesajlarını işleme
                    continue

                with self.state_lock: # Hafızaya yazarken diğer thread'leri kilitle
                    # Yeni bir drone keşfedildiyse kayıt aç
                    if drone_id not in self._drones_state:
                        self._drones_state[drone_id] = {
                            "lat": 0.0, "lon": 0.0, "alt": 0.0,
                            "mode": "UNKNOWN", "armed": False, "att": {},
                            "speed": 0.0, "seq": 0, "last_seen": time.time()
                        }
                        print(f"[Vehicle] Yeni drone keşfedildi ID: {drone_id}")

                    # Drone'un son görülme zamanını güncelle
                    state = self._drones_state[drone_id]
                    state["last_seen"] = time.time()

                    # Gelen mesajın tipine göre veriyi parse et (ayrıştır)
                    msg_type = msg.get_type()

                    if msg_type == 'GLOBAL_POSITION_INT': # Konum Verisi
                        state["lat"] = msg.lat / 1e7 # Enlem (7 hane kaydırılmış gelir)
                        state["lon"] = msg.lon / 1e7 # Boylam
                        state["alt"] = msg.relative_alt / 1e3 # Göreceli irtifa (metre)
                    
                    elif msg_type == 'HEARTBEAT': # Durum Verisi
                        state["mode"] = mavutil.mode_string_v10(msg) # Uçuş Modu (GUIDED, RTL vb.)
                        # Silahlı (ARM) durumu kontrolü
                        state["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                    
                    elif msg_type == 'ATTITUDE': # Yönelim Verisi
                        yaw_deg = math.degrees(msg.yaw) if math.degrees(msg.yaw) >= 0 else math.degrees(msg.yaw) + 360.0
                        roll_deg = math.degrees(msg.roll) if math.degrees(msg.roll) >= 0 else math.degrees(msg.roll) + 360.0
                        pitch_deg = math.degrees(msg.pitch) if math.degrees(msg.pitch) >= 0 else math.degrees(msg.pitch) + 360.0
                        yaw_speed = float(msg.yawspeed)
                        state["att"] = {"yaw": yaw_deg, "roll": roll_deg, "pitch": pitch_deg, "yaw_speed": yaw_speed}
                    
                    elif msg_type == 'VFR_HUD': # Hız ve İrtifa Özeti
                        state["speed"] = msg.groundspeed # Yer hızı (m/s)
                    
                    elif msg_type == 'STATUSTEXT': # Drone'dan gelen metin logları
                        # print(f"[Drone {drone_id} Log] {msg.text}")
                        pass
                    
                    elif msg_type == "MISSION_ITEM_REACHED": # Drone'ın AUTO mod'daki waypoint'i
                        seq = int(msg.seq)
                        state["seq"] = seq if seq else 0

            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[Vehicle] Listener Hatası: {e}")

    def _request_initial_telemetry(self):
        """Drone'a 'şu verileri saniyede X kez gönder' komutu iletir."""
        # İstenen mesaj tipleri ve Hz değerleri
        msgs = [
            ('GLOBAL_POSITION_INT', 5), # Konum 5Hz
            ('ATTITUDE', 5),            # Yönelim 5Hz
            ('VFR_HUD', 2),             # Hız 2Hz
            ('STATUSTEXT', 1)           # Loglar 1Hz
        ]
        for msg_name, hz in msgs:
            try:
                msg_id = getattr(mavutil.mavlink, f"MAVLINK_MSG_ID_{msg_name}")
                # Tüm sistemlere (target_system=0) mesaj aralığı ayarı gönder
                # TODO: burasi calismayabilir
                self.vehicle.mav.command_long_send(
                    0, 0, # Broadcast (tüm drone'lar)
                    mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                    msg_id, int(1e6 / hz), 0, 0, 0, 0, 0
                )
                print(f"[Vehicle] Drone'lardan {msg_name} verisi dinleniyor...")
            except Exception as e:
                print(e)

    # --- API / Veri Okuma Metodları (Anlık ve Hızlı) ---

    def get_all_drone_ids(self):
        """Hafızadaki tüm drone ID'lerini liste olarak döndürür."""
        return list(self._drones_state.keys())

    def _get_drone_state(self, drone_id: int):
        """Belirli bir drone'un verisini hafızadan güvenli çeker."""
        with self.state_lock:
            return self._drones_state.get(drone_id, None)

    def get_pos(self, drone_id: int):
        """Drone'un son bilinen konumunu döner (Bloklama yapmaz)."""
        state = self._get_drone_state(drone_id)
        return (state["lat"], state["lon"], state["alt"]) if state else (0.0, 0.0, 0.0)

    def get_mode(self, drone_id: int):
        """Drone'un son bilinen modunu döner."""
        state = self._get_drone_state(drone_id)
        return state["mode"] if state else "UNKNOWN"

    def is_armed(self, drone_id: int):
        """Drone ARM durumunu döner (1: Armed, 0: Disarmed)."""
        state = self._get_drone_state(drone_id)
        return 1 if state and state["armed"] else 0

    def get_roll(self, drone_id: int):
        """Drone'un son bilinen yatma açısını (roll) döner."""
        state = self._get_drone_state(drone_id)
        return state["att"]["roll"] if state else 0.0

    def get_pitch(self, drone_id: int):
        """Drone'un son bilinen yunuslama açısını (pitch) döner."""
        state = self._get_drone_state(drone_id)
        return state["att"]["pitch"] if state else 0.0

    def get_yaw(self, drone_id: int):
        """Drone'un son bilinen baş açısını (heading) döner."""
        state = self._get_drone_state(drone_id)
        return state["att"]["yaw"] if state else 0.0
    
    def yaw_speed(self, drone_id: int):
        state = self._get_drone_state(drone_id)
        return state["att"]["yaw_speed"] if state else 0.0

    def get_speed(self, drone_id: int):
        """Drone'un son bilinen yer hızını döner."""
        state = self._get_drone_state(drone_id)
        return state["speed"] if state else 0.0
    
    def get_miss_wp(self, drone_id: int):
        """Drone'un AUTO uçuşundaki waypoint bilgisi."""
        state = self._get_drone_state(drone_id)
        return state["seq"] if state else 0

    def get_home_pos(self, drone_id):
        """Drone'un kalkış yaptığı koordinatı döndürür."""
        if drone_id in self.TAKEOFF_POS.keys():
            if self.TAKEOFF_POS.get(drone_id) is None or self.TAKEOFF_POS.get(drone_id) == (0.0, 0.0, 0.0):
                return None
            return self.TAKEOFF_POS.get(drone_id)
        return None

    # --- Komut Gönderme Metodları ---

    def arm_disarm(self, arm: bool, force_arm: bool=False, drone_id: int=None):
        """Drone'u ARM veya DISARM eder."""

        if drone_id is None:
            drone_id = self.drone_id

        ARM = 1 if arm else 0
        FORCE_ARM = 21196 if force_arm else 0 # Güvenlik kilidini aşmak gerekirse

        try:
            self.vehicle.mav.command_long_send(
                drone_id, self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                ARM, FORCE_ARM, 0, 0, 0, 0, 0
            )
            print(f"{drone_id}>> ARM Edildi" if arm else f"{drone_id}>> DISARM Edildi")
        except Exception as e:
            print(e)

    def set_mode(self, mode: str, drone_id: int=None):
        """Drone'un uçuş modunu değiştirir (GUIDED, RTL, AUTO vb.)."""

        if drone_id is None:
            drone_id = self.drone_id

        mode = mode.upper()

        try:
            if mode == "RTL":
                self.vehicle.mav.command_long_send(drone_id, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0, 0, 0, 0, 0, 0, 0, 0)
            elif mode == "AUTO":
                self.vehicle.mav.command_long_send(drone_id, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_MISSION_START, 0, 0, 0, 0, 0, 0, 0, 0)
            else:
                mode_map = self.vehicle.mode_mapping() # Drone'un desteklediği mod haritasını al
                if mode not in mode_map:
                    Exception(f"{drone_id}>> Geçersiz mod: {mode}")
                    return
                self.vehicle.mav.command_long_send(
                    drone_id, self.vehicle.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_map[mode], 0, 0, 0, 0, 0
                )
        except Exception as e:
            print(e)

    def multiple_takeoff(self, alt, drone_id: int=None):
        """Drone'a kalkış (Takeoff) emri verir."""

        if drone_id is None:
            drone_id = self.drone_id

        try:
            # Mevcut konumu kalkış konumu (Home) olarak işaretle
            pos = self.get_pos(drone_id)
            self.TAKEOFF_POS[drone_id] = pos

            self.vehicle.mav.command_long_send(
                drone_id, self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, alt
            )
        except Exception as e:
            print(e)

    def move_drone(self, rota, drone_id: int=None):
        if drone_id is None:
            drone_id = self.drone_id
        
        try:
            vx, vy, vz = rota

            self.vehicle.mav.set_position_target_local_ned_send(
                0,  # Timestamp
                drone_id, self.vehicle.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_NED,  # Koordinat sistemi
                0b0000111111000111,  # Type mask (sadece hız kullanılacak)
                0, 0, 0,  # Pozisyon (kullanılmıyor)
                vx, vy, vz,  # Hız (m/s)
                0, 0, 0,  # İvme (kullanılmıyor)
                0, 0)  # Yaw, yaw_rate (kullanılmıyor)

        except Exception as e:
            print(e)
            return e

    def go_to(self, loc, alt: float = None, drone_id: int=None):
        """Drone'u belirli bir koordinata yönlendirir (GUIDED mod gerektirir)."""

        if drone_id is None:
            drone_id = self.drone_id

        try:
            if len(loc) < 2:
                print("2den az")
                Exception(f"Geçersiz konum: {loc}")
                return

            lat, lon = loc[0], loc[1]

            if alt == None:
                alt = self.get_pos(drone_id=drone_id)[2]
                if alt <= 1 or alt >= 20:
                    print(f"{drone_id}>> Yukseklik verisi cekmede sorun cikti, yukseklik 5mt yapildi.")
                    alt = 5

            self.vehicle.mav.send(mavutil.mavlink.MAVLink_set_position_target_global_int_message(
                0, drone_id, self.vehicle.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                0b110111111000, # Sadece pozisyon hedeflerini kullan (hız/ivme maskele)
                int(lat * 1e7), int(lon * 1e7), alt,
                0, 0, 0, 0, 0, 0, 0, 0
            ))
        except Exception as e:
            print(e)
    
    def scan_area_wpler(self, center_loc, alt, area_meter, distance_meter):
        """Bir alanı taramak için 'Yılan' (Zig-Zag) şeklinde waypoint listesi üretir."""
        
        met = -1 * (area_meter / 2)
        sign = 1
        steps = int(area_meter / distance_meter)
        wpler = []

        try:
            if len(center_loc) != 2:
                Exception(f"Geçersiz konum: {center_loc}")
                return

            for i in range(steps + 1):
                lat = center_loc[0] + (met + distance_meter * i) * self.DEG
                lon = center_loc[1] + (met * sign) * self.DEG
                sign *= -1 # Yönü tersine çevir
                wpler.append([lat, lon, alt])

            return wpler
        except Exception as e:
            print(e)

    def on_location(self, loc, seq: int=0, sapma: float = 1.5, drone_id: int = None, drone_loc: tuple = None):
        """Drone belirtilen konuma ulaştı mı kontrol eder (Sapma metre cinsindendir)."""

        if drone_id is None and drone_loc is None:
            drone_id = self.drone_id

        drone_pos = drone_loc if drone_loc is not None else self.get_pos(drone_id)[:2]

        try:
            if not drone_pos or drone_pos == (0.0, 0.0): return Exception(f"{drone_id}>> Drone konum verisi alinamadi")
            
            dist = geodesic(drone_pos[:2], loc[:2]).meters # İki nokta arası mesafe

            return (dist <= sapma) and (seq == self.get_miss_wp(drone_id) if seq else True)
        except Exception as e:
            print(e)

    def set_yaw(self, turn_angle, default_speed: int=30, drone_id: int=None):
        if drone_id is None:
            drone_id = self.drone_id
        
        try:
            if turn_angle > 0:
                clock_wise = 1
            else:
                clock_wise = -1
                turn_angle *= -1

            self.vehicle.mav.command_long_send(
                drone_id,
                self.vehicle.target_component, # Hedef bileşen ID
                mavutil.mavlink.MAV_CMD_CONDITION_YAW, # Yaw kontrol komutu
                0,                       # Confirmation (0: İlk komut)
                int(turn_angle),               # Yaw açısı
                default_speed,                      # Dönüş hızı (derece/saniye)
                clock_wise,                       # Yön (1: Saat yönü, -1: Saat tersi)
                1,           # Açı göreceli mi? (0: Global, 1: Relative)
                0, 0, 0                  # Kullanılmayan parametreler
            )
            
        except Exception as e:
            return e

    def set_servo(self, channel: int, pwm: int, drone_id: int = None):
        """Belirli bir servo kanalının PWM değerini ayarlar."""

        if drone_id is None:
            drone_id = self.drone_id

        try:
            if pwm > 2000 or pwm < 1000:
                Exception(f"{drone_id}>> Servo PWM degeri 1000-2000 deger araliginda olmali verilen deger aralik disinda: {pwm}")

            self.vehicle.mav.command_long_send(
                drone_id, self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0,
                channel, pwm, 0, 0, 0, 0, 0
            )
            print(f"{drone_id}>> Servo PWM: {pwm}")
        except Exception as e:
            print(e)
    
    # TODO: send_all_waypoints fonksiyonunu getir

    def close(self):
        """Bağlantıyı ve dinleyici thread'i düzgünce kapatır."""
        
        if not self.stop_event.is_set():
            self.stop_event.set() # Thread döngüsünü bitir
        
        if hasattr(self, 'vehicle'):
            self.vehicle.close() # Seri portu serbest bırak

def calc_distance(loc1, loc2):
    return geodesic(loc1[:2], loc2[:2]).meters

def calc_pos(loc, distance, bearing):
    return list(geodesic(kilometers=distance/1000).destination(loc, bearing))[:2]

def failsafe(vehicle: Vehicle):
    def failsafe_drone_id(vehicle: Vehicle, drone_id: int):
        home_pos = vehicle.get_home_pos(drone_id)

        if home_pos is not None:
            print(f"{drone_id}>> Kalkis konumuna donuyor")
            vehicle.set_mode(mode="GUIDED", drone_id=drone_id)
            time.sleep(1)
            vehicle.go_to(loc=home_pos, drone_id=drone_id)

            while not vehicle.on_location(loc=home_pos, sapma=1, drone_id=drone_id):
                time.sleep(0.5)
            
            print(f"{drone_id}>> LAND aliyor")
            vehicle.set_mode(mode="LAND", drone_id=drone_id)
            time.sleep(1)
        
        else:
            print(f"{drone_id}>> RTL alıyor")
            vehicle.set_mode(mode="RTL", drone_id=drone_id)


    thraeds = []
    for d_id in vehicle.get_all_drone_ids():
        args = (vehicle, d_id)

        thrd = threading.Thread(target=failsafe_drone_id, args=args)
        thrd.start()
        thraeds.append(thrd)


    for t in thraeds:
        t.join()

    print(f"{vehicle.get_all_drone_ids()} id'li Drone(lar) Failsafe aldi")