import cv2
import time

def test_camera():
    print("Kamera test ediliyor... (Kapatmak için 'q' tuşuna basın)")
    # DirectShow ile dene
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("DSHOW başarısız, normal deneniyor...")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("HATA: Kamera hiçbir şekilde açılamadı!")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kare alınamıyor...")
            break
        
        cv2.imshow('Kamera Testi', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Test bitti.")

if __name__ == "__main__":
    test_camera()
