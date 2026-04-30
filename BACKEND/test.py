from libs.image_proccesser import Handler
import threading


handler = Handler(stop_event=threading.Event(), window_name="a")
t = threading.Thread(target=handler.udp_camera, args=("192.168.31.80", 9999), daemon=True)
t.start()
t.join()
