import streamlit as st
import datetime

st.set_page_config(page_title="Sistem Absensi PTK", page_icon="📋", layout="wide")

# Inisialisasi Session State Login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Halaman Login
if not st.session_state["logged_in"]:
    st.title("🔑 Login Presensi PTK")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login", type="primary"):
        if username == "admin" and password == "admin123":
            st.session_state["logged_in"] = True
            st.session_state["user"] = "Super Admin"
            st.rerun()
        else:
            st.error("Username atau Password salah!")

# Halaman Utama Aplikasi
else:
    st.sidebar.title(f"Aplikasi PTK ({st.session_state['user']})")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    menu = st.sidebar.radio("Navigasi Menu", ["Dashboard & Absensi", "Data PTK", "Pengaturan"])

    if menu == "Dashboard & Absensi":
        st.header("📸 Dashboard & Presensi Wajah")
        col1, col2 = st.columns(2)
        
        with col1:
            nama = st.selectbox("Pilih Nama Pegawai", ["Budi Santoso", "Siti Rahma"])
            jenis = st.radio("Jenis Presensi", ["Masuk", "Pulang"])
        
        with col2:
            foto = st.camera_input("Ambil Foto Presensi")
            if st.button("Kirim Presensi", type="primary"):
                if foto:
                    st.success(f"Presensi {jenis} berhasil direkam untuk {nama} pada {datetime.datetime.now().strftime('%H:%M:%S')}")
                else:
                    st.warning("Kamera wajib digunakan!")

    elif menu == "Data PTK":
        st.header("👥 Data Tenaga Pendidik & Kependidikan")
        data_ptk = [
            {"NIP": "198501012010011001", "Nama": "Budi Santoso", "Golongan": "III/c", "Jabatan": "Guru Matematika"},
            {"NIP": "199002022015022002", "Nama": "Siti Rahma", "Golongan": "III/b", "Jabatan": "Guru Bahasa Indonesia"}
        ]
        st.dataframe(data_ptk, use_container_width=True)

    elif menu == "Pengaturan":
        st.header("⚙️ Pengaturan Jam Kerja")
        st.time_input("Batas Jam Masuk", datetime.time(7, 30))
        st.time_input("Batas Jam Pulang", datetime.time(14, 0))
        st.text_input("Titik Koordinat Pusat", "-5.147665, 119.432731")
        if st.button("Simpan Pengaturan"):
            st.success("Pengaturan berhasil disimpan!")
