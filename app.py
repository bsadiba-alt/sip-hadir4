import sqlite3
import math
import json
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from datetime import datetime

# ==========================================
# 1. KONFIGURASI HALAMAN & CSS RESPONSIF MOBILE
# ==========================================
st.set_page_config(
    page_title="SIP-HADIR 4", 
    layout="wide", 
    page_icon="🔐",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }
        .stButton > button, .stDownloadButton > button {
            width: 100% !important;
            border-radius: 8px !important;
            height: 3rem !important;
            font-weight: bold !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
        [data-testid="stCameraInput"] {
            width: 100% !important;
        }
    }
    .stApp { background-color: #F8F9FA; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E9ECEF;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE SETUP & INITIALIZATION
# ==========================================
DB_FILE = "sip_hadir4.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_lat REAL NOT NULL,
            target_lng REAL NOT NULL,
            radius_meters REAL DEFAULT 50.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            nip TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('cabdin', 'sekolah', 'asn')),
            school_id TEXT,
            face_encoding TEXT,
            FOREIGN KEY (school_id) REFERENCES schools (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nip TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            distance_meters REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (nip) REFERENCES users (nip)
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO schools VALUES ('SCH-01', 'SMKN 1 Wilayah 4', -5.147665, 119.432732, 50.0)")
        cursor.execute("INSERT INTO users VALUES ('ADMIN-CABDIN', 'Kepala Cabang Dinas', 'ADMIN-CABDIN', 'cabdin', 'SCH-01', NULL)")
        cursor.execute("INSERT INTO users VALUES ('ADMIN-SMK1', 'Admin SMKN 1', 'ADMIN-SMK1', 'sekolah', 'SCH-01', NULL)")
        cursor.execute("INSERT INTO users VALUES ('198501012010011001', 'Budi Santoso, S.Pd (Guru)', '198501012010011001', 'asn', 'SCH-01', NULL)")
        conn.commit()
    conn.close()

# ==========================================
# 3. LOGIKA BIOMETRIK WAJAH & GEO-TAGGING
# ==========================================
def calculate_haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def extract_face_features(image_bytes):
    try:
        image_bytes.seek(0)
        img = Image.open(image_bytes).convert('L')
        w, h = img.size
        cx, cy = w // 2, h // 2
        crop_size = min(w, h) // 2
        
        left = max(0, cx - crop_size // 2)
        top = max(0, cy - crop_size // 2)
        right = min(w, cx + crop_size // 2)
        bottom = min(h, cy + crop_size // 2)
        
        face_cropped = img.crop((left, top, right, bottom))
        face_resized = face_cropped.resize((64, 64))
        
        vector = np.array(face_resized, dtype=np.float32).flatten()
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector.tolist(), "Success"
    except Exception as e:
        return None, f"Gagal memproses gambar: {str(e)}"

def match_faces(encoding1, encoding2, threshold=0.55):
    if encoding1 is None or encoding2 is None:
        return False, 999.0
    v1 = np.array(encoding1, dtype=np.float32)
    v2 = np.array(encoding2, dtype=np.float32)
    distance = float(np.linalg.norm(v1 - v2))
    return distance < threshold, distance

# ==========================================
# 4. SESI LOG IN & NAVIGASI SIDEBAR
# ==========================================
init_db()

if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("🏛️ SIP-HADIR 4")
    st.caption("Sistem Presensi Biometrik - Cabang Dinas Wilayah 4")
    
    st.info("Log in menggunakan NIP sebagai Username & Password bawaan.")
    nip = st.text_input("NIP / Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Masuk Ke Sistem", type="primary"):
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE nip = ? AND password = ?", (nip, password)).fetchone()
        conn.close()
        if user:
            st.session_state['user'] = dict(user)
            st.rerun()
        else:
            st.error("NIP atau Password salah!")
    st.stop()

user = st.session_state['user']
st.sidebar.markdown("### 🏛️ SIP-HADIR 4")
st.sidebar.markdown(f"👤 **{user['name']}**")
st.sidebar.caption(f"Hak Akses: **{user['role'].upper()}** | NIP: {user['nip']}")

with st.sidebar.expander("🔑 Ganti Password"):
    new_pass = st.text_input("Password Baru", type="password")
    confirm_pass = st.text_input("Konfirmasi Password", type="password")
    if st.button("Simpan Password Baru"):
        if new_pass and new_pass == confirm_pass:
            conn = get_db()
            conn.execute("UPDATE users SET password = ? WHERE nip = ?", (new_pass, user['nip']))
            conn.commit()
            conn.close()
            st.success("Password diperbarui!")
        else:
            st.warning("Password tidak cocok!")

if st.sidebar.button("Keluar (Logout)"):
    st.session_state['user'] = None
    st.rerun()

# ==========================================
# 5. MODUL PERAN PENGGUNA
# ==========================================

# ------------------------------------------
# A. PERAN ASN / GURU (KAMERA FIX SELALU MUNCUL)
# ------------------------------------------
if user['role'] == 'asn':
    st.title("📌 Presensi Kehadiran ASN")
    
    conn = get_db()
    school = conn.execute("SELECT * FROM schools WHERE id = ?", (user['school_id'],)).fetchone()
    db_user = conn.execute("SELECT * FROM users WHERE nip = ?", (user['nip'],)).fetchone()
    conn.close()

    # ALUR 1: Registrasi Wajah Perdana
    if db_user['face_encoding'] is None:
        st.warning("⚠️ Biometrik wajah Anda belum terdaftar. Lakukan pendaftaran awal di bawah ini.")
        img_file = st.camera_input("Ambil Foto Referensi Wajah", key="cam_reg")
        if img_file:
            encoding, msg = extract_face_features(img_file)
            if encoding:
                conn = get_db()
                conn.execute("UPDATE users SET face_encoding = ? WHERE nip = ?", (json.dumps(encoding), user['nip']))
                conn.commit()
                conn.close()
                st.success("✅ Pendaftaran wajah berhasil! Silakan lakukan presensi.")
                st.session_state['user']['face_encoding'] = json.dumps(encoding)
                st.rerun()
            else:
                st.error(msg)

    # ALUR 2: Presensi Harian (GPS & Kamera Berjalan Independen)
    else:
        st.subheader("📍 Lokasi & Verifikasi Presensi")
        
        curr_lat = st.query_params.get("lat", None)
        curr_lng = st.query_params.get("lng", None)
        
        # Inisialisasi Status GPS
        is_in_radius = False
        distance = 0.0
        
        if not curr_lat or not curr_lng:
            st.warning("🔄 Sedang mendeteksi lokasi GPS... Mohon izinkan lokasi pada browser HP Anda.")
            gps_script = """
            <script>
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        const url = new URL(window.parent.location.href);
                        if (!url.searchParams.get("lat")) {
                            url.searchParams.set("lat", lat);
                            url.searchParams.set("lng", lng);
                            window.parent.location.replace(url.href);
                        }
                    },
                    function(error) {
                        console.log("GPS Error: " + error.message);
                    },
                    { enableHighAccuracy: true, timeout: 7000 }
                );
            }
            </script>
            """
            components.html(gps_script, height=0)
            if st.button("🔄 Ambil Ulang Koordinat GPS"):
                st.rerun()
        else:
            curr_lat = float(curr_lat)
            curr_lng = float(curr_lng)
            distance = calculate_haversine(curr_lat, curr_lng, school['target_lat'], school['target_lng'])
            is_in_radius = distance <= school['radius_meters']
            
            st.write(f"🏢 **Sekolah:** {school['name']}")
            st.write(f"📏 **Jarak Anda:** `{distance:.1f} Meter` dari sekolah")
            
            if is_in_radius:
                st.success("✅ Lokasi Valid: Anda berada di area sekolah.")
            else:
                st.error(f"❌ Lokasi Tidak Valid: Di luar radius ({school['radius_meters']} m).")

        st.write("---")
        
        # KAMERA DILETAKKAN DI LUAR IF/ELSE AGAR SELALU MUNCUL DI LAYAR
        img_scan = st.camera_input("Pindai Wajah Presensi", key="cam_presensi")
        
        if img_scan:
            if not curr_lat or not curr_lng:
                st.error("🚫 Gagal Presensi: Lokasi GPS belum terdeteksi! Aktifkan GPS HP Anda dan klik 'Ambil Ulang Koordinat GPS'.")
            else:
                scan_encoding, msg = extract_face_features(img_scan)
                if not scan_encoding:
                    st.error(msg)
                else:
                    saved_encoding = json.loads(db_user['face_encoding'])
                    is_match, dist = match_faces(scan_encoding, saved_encoding, threshold=0.55)

                    if is_match and is_in_radius:
                        conn = get_db()
                        conn.execute("INSERT INTO attendance (nip, lat, lng, distance_meters, status) VALUES (?, ?, ?, ?, ?)",
                                     (user['nip'], curr_lat, curr_lng, distance, 'HADIR'))
                        conn.commit()
                        conn.close()
                        st.balloons()
                        st.success("🎉 PRESENSI BERHASIL DICATAT!")
                    else:
                        if not is_match:
                            st.error(f"🚫 Presensi Ditolak: Wajah tidak cocok! (Kemiripan: {dist:.2f})")
                        if not is_in_radius:
                            st.error("🚫 Presensi Ditolak: Anda berada di luar area sekolah!")

# ------------------------------------------
# B. PERAN SEKOLAH (ADMIN SEKOLAH)
# ------------------------------------------
elif user['role'] == 'sekolah':
    st.title("🏫 Panel Pengawasan Sekolah")
    
    conn = get_db()
    school = conn.execute("SELECT * FROM schools WHERE id = ?", (user['school_id'],)).fetchone()
    logs = conn.execute('''
        SELECT a.timestamp as Waktu, u.nip as NIP, u.name as Nama, a.distance_meters as Jarak_Meter, a.status as Status 
        FROM attendance a JOIN users u ON a.nip = u.nip 
        WHERE u.school_id = ? ORDER BY a.timestamp DESC
    ''', (user['school_id'],)).fetchall()
    
    teachers = conn.execute('''
        SELECT nip as NIP, name as Nama_Lengkap, 
               CASE WHEN face_encoding IS NOT NULL THEN '✅ Terdaftar' ELSE '❌ Belum' END as Status_Wajah
        FROM users WHERE school_id = ? AND role = 'asn'
    ''', (user['school_id'],)).fetchall()
    conn.close()

    st.caption(f"Unit Kerja: **{school['name']}**")
    tab1, tab2, tab3 = st.tabs(["📊 Laporan Kehadiran", "👥 Kelola Guru ASN", "⚙️ GPS Sekolah"])
    
    with tab1:
        if logs:
            st.dataframe(pd.DataFrame([dict(row) for row in logs]), use_container_width=True)
        else:
            st.info("Belum ada data presensi.")

    with tab2:
        c_add, c_list = st.columns([1, 1.2])
        with c_add:
            st.markdown("#### ➕ Tambah Guru Baru")
            st.caption("Password otomatis sama dengan NIP.")
            new_nip = st.text_input("NIP Baru (18 Digit)", key="new_nip")
            new_name = st.text_input("Nama Lengkap & Gelar", key="new_name")
            
            if st.button("Simpan Data Guru", type="primary"):
                if new_nip and new_name:
                    conn = get_db()
                    if conn.execute("SELECT nip FROM users WHERE nip = ?", (new_nip,)).fetchone():
                        st.error("⚠️ NIP sudah terdaftar!")
                        conn.close()
                    else:
                        conn.execute("INSERT INTO users VALUES (?, ?, ?, 'asn', ?, NULL)",
                                     (new_nip, new_name, new_nip, user['school_id']))
                        conn.commit()
                        conn.close()
                        st.success(f"Guru {new_name} berhasil ditambahkan!")
                        st.rerun()
                else:
                    st.warning("Lengkapi NIP dan Nama!")
                    
        with c_list:
            st.markdown("#### 👥 Daftar Guru Terdaftar")
            if teachers:
                st.dataframe(pd.DataFrame([dict(t) for t in teachers]), use_container_width=True)
                sel_nip = st.selectbox("Pilih NIP Guru", [t['NIP'] for t in teachers])
                
                cr, cd, cf = st.columns(3)
                with cr:
                    if st.button("Reset Password"):
                        conn = get_db()
                        conn.execute("UPDATE users SET password = nip WHERE nip = ?", (sel_nip,))
                        conn.commit()
                        conn.close()
                        st.success("Password di-reset ke NIP!")
                with cd:
                    if st.button("Hapus Guru"):
                        conn = get_db()
                        conn.execute("DELETE FROM users WHERE nip = ?", (sel_nip,))
                        conn.commit()
                        conn.close()
                        st.warning("Data guru dihapus!")
                        st.rerun()
                with cf:
                    if st.button("🔄 Reset Wajah"):
                        conn = get_db()
                        conn.execute("UPDATE users SET face_encoding = NULL WHERE nip = ?", (sel_nip,))
                        conn.commit()
                        conn.close()
                        st.success("Wajah di-reset!")
                        st.rerun()

    with tab3:
        n_lat = st.number_input("Target Latitude", value=school['target_lat'], format="%.6f")
        n_lng = st.number_input("Target Longitude", value=school['target_lng'], format="%.6f")
        n_rad = st.number_input("Radius Toleransi (Meter)", value=school['radius_meters'])
        if st.button("Simpan Koordinat GPS"):
            conn = get_db()
            conn.execute("UPDATE schools SET target_lat=?, target_lng=?, radius_meters=? WHERE id=?",
                         (n_lat, n_lng, n_rad, school['id']))
            conn.commit()
            conn.close()
            st.success("Koordinat diperbarui!")

# ------------------------------------------
# C. PERAN CABANG DINAS (SUPER ADMIN)
# ------------------------------------------
elif user['role'] == 'cabdin':
    st.title("🏛️ Executive Dashboard - Wilayah 4")
    
    conn = get_db()
    total_asn = conn.execute("SELECT COUNT(*) FROM users WHERE role='asn'").fetchone()[0]
    total_hadir = conn.execute("SELECT COUNT(DISTINCT nip) FROM attendance WHERE DATE(timestamp) = DATE('now')").fetchone()[0]
    
    logs_all = conn.execute('''
        SELECT a.timestamp as Waktu, s.name as Sekolah, u.nip as NIP, u.name as Nama, a.status as Status, a.distance_meters as Jarak_Meter 
        FROM attendance a 
        JOIN users u ON a.nip = u.nip 
        JOIN schools s ON u.school_id = s.id 
        ORDER BY a.timestamp DESC
    ''').fetchall()
    
    users_all = conn.execute("SELECT u.nip as NIP, u.name as Nama, u.role as Peran, s.name as Sekolah FROM users u LEFT JOIN schools s ON u.school_id = s.id").fetchall()
    conn.close()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total ASN", f"{total_asn} Orang")
    m2.metric("Hadir Hari Ini", f"{total_hadir} Orang")
    m3.metric("Tingkat Kehadiran", f"{(total_hadir/total_asn*100) if total_asn > 0 else 0:.1f}%")

    st.write("---")
    tab_log, tab_export, tab_user, tab_school = st.tabs([
        "📑 Log Real-Time", 
        "📥 Export Google Sheets", 
        "👥 Kelola Pengguna", 
        "🏫 Tambah Sekolah"
    ])
    
    with tab_log:
        if logs_all:
            st.dataframe(pd.DataFrame([dict(r) for r in logs_all]), use_container_width=True)
        else:
            st.info("Belum ada log presensi.")

    with tab_export:
        st.markdown("#### 📥 Rekap Presensi (Impor Google Sheets)")
        if logs_all:
            df_export = pd.DataFrame([dict(r) for r in logs_all])
            df_export['Waktu'] = pd.to_datetime(df_export['Waktu'])
            
            rekap_type = st.radio("Pilih Filter Laporan:", ["Semua Data", "Harian", "Rentang Tanggal (Mingguan/Bulanan)"], horizontal=True)
            filtered_df = df_export.copy()
            
            if rekap_type == "Harian":
                tgl = st.date_input("Tanggal", value=datetime.today())
                filtered_df = df_export[df_export['Waktu'].dt.date == tgl]
            elif rekap_type == "Rentang Tanggal (Mingguan/Bulanan)":
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tgl_m = st.date_input("Mulai", value=datetime.today())
                with col_t2:
                    tgl_s = st.date_input("Sampai", value=datetime.today())
                filtered_df = df_export[(df_export['Waktu'].dt.date >= tgl_m) & (df_export['Waktu'].dt.date <= tgl_s)]

            filtered_df['Waktu'] = filtered_df['Waktu'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.write(f"📊 Total Data Terfilter: `{len(filtered_df)}` baris.")
            st.dataframe(filtered_df, use_container_width=True)
            
            csv_bytes = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="🟢 Download File CSV (Siap Impor ke Google Sheets)",
                data=csv_bytes,
                file_name=f"rekap_presensi_wil4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.info("Data belum tersedia.")

    with tab_user:
        st.write("#### Daftar Pengguna Sistem")
        st.dataframe(pd.DataFrame([dict(u) for u in users_all]), use_container_width=True)

    with tab_school:
        st.write("#### ➕ Tambah Sekolah Baru")
        s_id = st.text_input("ID Sekolah (misal: SCH-02)")
        s_name = st.text_input("Nama Sekolah (misal: SMAN 1 Wajo)")
        s_lat = st.number_input("Latitude", value=-4.0, format="%.6f")
        s_lng = st.number_input("Longitude", value=120.0, format="%.6f")
        s_rad = st.number_input("Radius (Meter)", value=50.0)
        
        if st.button("Simpan Sekolah Baru", type="primary"):
            if s_id and s_name:
                conn = get_db()
                check_school = conn.execute("SELECT id FROM schools WHERE id = ?", (s_id,)).fetchone()
                check_user = conn.execute("SELECT nip FROM users WHERE nip = ?", (f"ADMIN-{s_id}",)).fetchone()
                
                if check_school:
                    st.error(f"⚠️ ID Sekolah '{s_id}' sudah digunakan!")
                    conn.close()
                elif check_user:
                    st.error(f"⚠️ User Admin 'ADMIN-{s_id}' sudah ada di sistem.")
                    conn.close()
                else:
                    try:
                        conn.execute("INSERT INTO schools VALUES (?, ?, ?, ?, ?)", (s_id, s_name, s_lat, s_lng, s_rad))
                        conn.execute("INSERT INTO users VALUES (?, ?, ?, 'sekolah', ?, NULL)", (f"ADMIN-{s_id}", f"Admin {s_name}", f"ADMIN-{s_id}", s_id))
                        conn.commit()
                        st.success(f"Sekolah {s_name} berhasil ditambahkan!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Gagal menyimpan: Terjadi bentrokan data di database.")
                    finally:
                        conn.close()
            else:
                st.warning("⚠️ ID Sekolah dan Nama Sekolah wajib diisi!")
