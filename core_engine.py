import math
import numpy as np
import face_recognition
import io

def hitung_jarak_gps(lat1, lon1, lat2, lon2):
    """
    Menghitung jarak dua titik koordinat dalam meter menggunakan Formula Haversine.
    """
    R = 6371000  # Radius bumi dalam meter
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def ekstrak_vector_wajah(foto_bytes):
    """
    Mengekstrak encoding 128-dimensi dari foto master JPEG.
    """
    try:
        img = face_recognition.load_image_file(io.BytesIO(foto_bytes))
        encodings = face_recognition.face_encodings(img)
        if len(encodings) > 0:
            return True, encodings[0].tolist(), "Ekstraksi wajah berhasil."
        else:
            return False, None, "Wajah tidak terdeteksi pada foto. Pastikan posisi wajah tegak dan pencahayaan cukup."
    except Exception as e:
        return False, None, f"Terjadi kesalahan saat memproses gambar: {str(e)}"

def verifikasi_wajah_dipertajam(foto_input_bytes, vector_master_list, threshold=0.42):
    """
    Membandingkan foto selfie dengan vector master.
    Threshold default 0.42 untuk meminimalisir False Positive (Sangat Ketat).
    """
    try:
        img_input = face_recognition.load_image_file(io.BytesIO(foto_input_bytes))
        encodings_input = face_recognition.face_encodings(img_input)

        if not encodings_input:
            return False, "Wajah tidak terdeteksi pada kamera selfie.", 0.0

        vector_input = encodings_input[0]
        vector_master = np.array(vector_master_list)

        # Hitung jarak Euclidean
        distance = face_recognition.face_distance([vector_master], vector_input)[0]
        akurasi = round((1 - distance) * 100, 2)

        if distance <= threshold:
            return True, f"Verifikasi Wajah Cocok! (Akurasi: {akurasi}%)", distance
        else:
            return False, f"Wajah Tidak Cocok dengan Data Master! (Tingkat Kemiripan Rendah: {akurasi}%)", distance

    except Exception as e:
        return False, f"Gagal memproses verifikasi: {str(e)}", 0.0