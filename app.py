import streamlit as st
import pandas as pd
import sqlite3
import json
import io
from datetime import datetime
from streamlit_js_eval import get_geolocation
from core_engine import hitung_jarak_gps, ekstrak_vector_wajah, verifikasi_wajah_dipertajam

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Presensi Cabang Dinas",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MANAJEMEN DATABASE SQLITE ---
def get_db():
    conn = sqlite3.connect("presensi_cabdin.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Tabel Akun Admin
    c.execute('''CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT, 
                    nama_sekolah TEXT, 
                    role TEXT)''')

    # Tabel Pengaturan Sekolah
    c.execute('''CREATE TABLE IF NOT EXISTS pengaturan (
                    nama_sekolah TEXT PRIMARY KEY, 
                    jam_masuk TEXT, 
                    jam_pulang TEXT, 
                    latitude REAL, 
                    longitude REAL, 
                    radius_meter REAL)''')

    # Tabel Data Pegawai (PTK)
    c.execute('''CREATE TABLE IF NOT EXISTS pegawai (
                    nip TEXT PRIMARY KEY, 
                    nama TEXT, 
                    nama_sekolah TEXT, 
                    pangkat_gol TEXT, 
                    jabatan TEXT, 
                    foto_vector TEXT, 
                    foto_uploaded INTEGER DEFAULT 0)''')

    # Tabel Log Presensi
    c.execute('''CREATE TABLE IF NOT EXISTS presensi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    nip TEXT, 
                    tanggal TEXT, 
                    jam TEXT, 
                    status TEXT, 
                    lat REAL, 
                    lon REAL, 
                    keterangan TEXT)''')

    # Default Akun Super Admin
    c.execute("INSERT OR IGNORE INTO admin (username, password, nama_sekolah, role) VALUES ('superadmin', 'admin123', 'CABANG DINAS', 'superadmin')")
    conn.commit()

init_db()

# --- INISIALISASI SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = {}

# --- NAVIGASI UTAMA APPS ---
st.sidebar.title("🏫 Presensi Cabdin")
mode_akses = st.sidebar.radio("Pilih Portal Akses", ["Portal Presensi Mandiri (PTK)", "Login Admin / Manajemen"])

conn = get_db()

# ==============================================================================
# PORTAL 1: PRESENSI MANDIRI PTK (SELFIE & GPS)
# ==============================================================================
if mode_akses == "Portal Presensi Mandiri (PTK)":
    st.title("📸 Portal Presensi Mandiri PTK")
    st.caption("Silakan masukkan NIP, izinkan lokasi GPS browser, dan ambil foto selfie untuk presensi.")

    nip_input = st.text_input("Masukkan NIP Anda", placeholder="1985xxxxxxxxxxxxxx")

    if nip_input:
        c = conn.cursor()
        c.execute("SELECT nip, nama, nama_sekolah, foto_vector, foto_uploaded FROM pegawai WHERE nip=?", (nip_input.strip(),))
        pegawai = c.fetchone()

        if not pegawai:
            st.error("❌ NIP Anda belum terdaftar dalam sistem. Silakan hubungi Admin Sekolah.")
        elif pegawai[4] == 0 or not pegawai[3]:
            st.warning("⚠️ Foto master wajah Anda belum diunggah oleh Admin Sekolah. Silakan minta Admin Sekolah mengunggah foto master Anda.")
        else:
            nama_peg, sek_peg = pegawai[1], pegawai[2]
            vector_master = json.loads(pegawai[3])

            st.success(f"Dikenali: **{nama_peg}** | Unit Kerja: **{sek_peg}**")

            # 1. Validasi Lokasi GPS Browser
            st.subheader("📍 1. Deteksi Titik Koordinat GPS")
            loc = get_geolocation()

            if not loc:
                st.warning("🔄 Sedang mengambil koordinat lokasi... Pastikan GPS HP aktif dan Izin Akses Lokasi pada browser sudah DIKIK 'ALLOW/IZINKAN'.")
            else:
                lat_user = loc['coords']['latitude']
                lon_user = loc['coords']['longitude']
                st.info(f"Koordinat Anda: Lat `{lat_user:.6f}`, Lon `{lon_user:.6f}`")

                # Ambil data batas lokasi sekolah dari tabel pengaturan
                df_set = pd.read_sql_query(f"SELECT * FROM pengaturan WHERE nama_sekolah='{sek_peg}'", conn)

                if df_set.empty:
                    st.error(f"❌ Pengaturan titik koordinat untuk '{sek_peg}' belum diset oleh Super Admin.")
                else:
                    lat_sek = df_set.iloc[0]['latitude']
                    lon_sek = df_set.iloc[0]['longitude']
                    radius_max = df_set.iloc[0]['radius_meter']
                    jam_masuk_sek = df_set.iloc[0]['jam_masuk']

                    jarak = hitung_jarak_gps(lat_user, lon_user, lat_sek, lon_sek)
                    
                    st.metric(label="Jarak Anda ke Sekolah", value=f"{round(jarak, 1)} Meter", delta=f"Batas Maksimal: {radius_max} Meter")

                    if jarak > radius_max:
                        st.error(f"❌ Anda berada di luar area sekolah ({round(jarak)}m dari lokasi sekolah). Absen ditolak.")
                    else:
                        # 2. Camera Selfie & Verifikasi Wajah
                        st.subheader("📷 2. Verifikasi Wajah Selfie")
                        img_camera = st.camera_input("Ambil Foto Selfie Presensi")

                        if img_camera:
                            with st.spinner("Mengolah & Mencocokkan Vektor Wajah..."):
                                foto_bytes = img_camera.getvalue()
                                is_valid, msg, dist = verifikasi_wajah_dipertajam(foto_bytes, vector_master)

                                if not is_valid:
                                    st.error(f"❌ Verifikasi Wajah Gagal: {msg}")
                                else:
                                    st.success(f"✅ {msg}")

                                    now = datetime.now()
                                    tgl_str = now.strftime("%Y-%m-%d")
                                    jam_str = now.strftime("%H:%M:%S")

                                    status_absen = "Hadir (Tepat Waktu)"
                                    if jam_str[:5] > jam_masuk_sek:
                                        status_absen = "Hadir (Terlambat)"

                                    # Simpan Log Kehadiran
                                    c.execute("""
                                        INSERT INTO presensi (nip, tanggal, jam, status, lat, lon, keterangan)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (nip_input.strip(), tgl_str, jam_str, status_absen, lat_user, lon_user, f"Presensi Mandiri via HP (Jarak: {round(jarak)}m)"))
                                    conn.commit()

                                    st.balloons()
                                    st.success(f"🎉 Presensi Berhasil Dicatat! Jam: {jam_str} | Status: {status_absen}")

# ==============================================================================
# PORTAL 2: MANAJEMEN ADMIN (SUPER ADMIN & ADMIN SEKOLAH)
# ==============================================================================
else:
    if not st.session_state.logged_in:
        st.title("🔒 Login Admin / Manajemen")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk Ke Sistem")

            if submit:
                c = conn.cursor()
                c.execute("SELECT username, nama_sekolah, role FROM admin WHERE username=? AND password=?", (username.strip(), password.strip()))
                res = c.fetchone()
                if res:
                    st.session_state.logged_in = True
                    st.session_state.user_info = {"username": res[0], "sekolah": res[1], "role": res[2]}
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau Password Salah!")

    else:
        user = st.session_state.user_info
        st.sidebar.divider()
        st.sidebar.markdown(f"👤 **{user['username'].upper()}**")
        st.sidebar.caption(f"Role: **{user['role']}**\nSekolah: **{user['sekolah']}**")

        if st.sidebar.button("🚪 Logout / Keluar"):
            st.session_state.logged_in = False
            st.session_state.user_info = {}
            st.rerun()

        # DYNAMIC MENU BASED ON ROLE
        menu_items = ["Dashboard", "Rekapitulasi", "Data PTK"]
        if user['role'] == 'superadmin':
            menu_items.extend(["Pengaturan", "Upload Surat Cuti/Sakit", "Tambah Akun Admin Sekolah"])

        selected_menu = st.sidebar.selectbox("Menu Navigasi", menu_items)

        # ----------------------------------------------------------------------
        # MENU: DASHBOARD
        # ----------------------------------------------------------------------
        if selected_menu == "Dashboard":
            st.header("📊 Dashboard Kehadiran Real-Time")

            today = datetime.now().strftime("%Y-%m-%d")

            if user['role'] == 'superadmin':
                q_ptk = "SELECT nip, nama, nama_sekolah, jabatan FROM pegawai"
            else:
                q_ptk = f"SELECT nip, nama, nama_sekolah, jabatan FROM pegawai WHERE nama_sekolah='{user['sekolah']}'"

            df_ptk = pd.read_sql_query(q_ptk, conn)
            df_pres = pd.read_sql_query(f"SELECT nip, jam, status, keterangan FROM presensi WHERE tanggal='{today}'", conn)

            df_dash = pd.merge(df_ptk, df_pres, on='nip', how='left').fillna({'status': 'Belum Absen', 'jam': '-', 'keterangan': '-'})

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Pegawai (PTK)", len(df_dash))
            c2.metric("Hadir Tepat Waktu", len(df_dash[df_dash['status'] == 'Hadir (Tepat Waktu)']))
            c3.metric("Terlambat / Izin", len(df_dash[df_dash['status'].str.contains('Terlambat|Cuti|Sakit|Izin|Surat Tugas', case=False, na=False)]))
            c4.metric("Belum Absen", len(df_dash[df_dash['status'] == 'Belum Absen']))

            st.subheader(f"Daftar Status Kehadiran Hari Ini ({today})")
            st.dataframe(df_dash, use_container_width=True)

        # ----------------------------------------------------------------------
        # MENU: PENGATURAN (SUPER ADMIN ONLY)
        # ----------------------------------------------------------------------
        elif selected_menu == "Pengaturan":
            st.header("⚙️ Pengaturan Jam Kerja & Koordinat Sekolah (Super Admin)")

            list_sek = pd.read_sql_query("SELECT DISTINCT nama_sekolah FROM admin WHERE role='admin_sekolah'", conn)['nama_sekolah'].tolist()
            if not list_sek:
                st.info("Belum ada Admin Sekolah. Buat akun Admin Sekolah terlebih dahulu.")
            else:
                sel_sek = st.selectbox("Pilih Sekolah yang Akan Diatur", list_sek)
                curr_set = pd.read_sql_query(f"SELECT * FROM pengaturan WHERE nama_sekolah='{sel_sek}'", conn)

                val_jam_m = curr_set.iloc[0]['jam_masuk'] if not curr_set.empty else "07:30"
                val_jam_p = curr_set.iloc[0]['jam_pulang'] if not curr_set.empty else "16:00"
                val_lat = float(curr_set.iloc[0]['latitude']) if not curr_set.empty else 0.0
                val_lon = float(curr_set.iloc[0]['longitude']) if not curr_set.empty else 0.0
                val_rad = float(curr_set.iloc[0]['radius_meter']) if not curr_set.empty else 100.0

                with st.form("form_pengaturan"):
                    col_w1, col_w2 = st.columns(2)
                    jam_masuk = col_w1.text_input("Batas Jam Masuk (Format HH:MM)", value=val_jam_m)
                    jam_pulang = col_w2.text_input("Batas Jam Pulang (Format HH:MM)", value=val_jam_p)

                    col_k1, col_k2, col_k3 = st.columns(3)
                    lat = col_k1.number_input("Latitude Sekolah", value=val_lat, format="%.6f")
                    lon = col_k2.number_input("Longitude Sekolah", value=val_lon, format="%.6f")
                    radius = col_k3.number_input("Radius Akses (Meter)", value=val_rad, min_value=10.0, step=10.0)

                    if st.form_submit_button("Simpan Pengaturan"):
                        c = conn.cursor()
                        c.execute("""
                            INSERT OR REPLACE INTO pengaturan (nama_sekolah, jam_masuk, jam_pulang, latitude, longitude, radius_meter)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (sel_sek, jam_masuk.strip(), jam_pulang.strip(), lat, lon, radius))
                        conn.commit()
                        st.success(f"Pengaturan untuk {sel_sek} berhasil disimpan!")

        # ----------------------------------------------------------------------
        # MENU: REKAPITULASI
        # ----------------------------------------------------------------------
        elif selected_menu == "Rekapitulasi":
            st.header("📈 Rekapitulasi Presensi Pegawai")

            col_r1, col_r2 = st.columns(2)
            bln_opt = [f"{i:02d}" for i in range(1, 13)]
            sel_bln = col_r1.selectbox("Pilih Bulan", bln_opt, index=datetime.now().month - 1)

            if user['role'] == 'superadmin':
                sek_opts = ["Semua Sekolah"] + pd.read_sql_query("SELECT DISTINCT nama_sekolah FROM pegawai", conn)['nama_sekolah'].tolist()
                sel_sek_rekap = col_r2.selectbox("Filter Sekolah", sek_opts)
            else:
                sel_sek_rekap = user['sekolah']

            query_rekap = f"""
                SELECT p.tanggal, p.jam, pg.nama_sekolah, pg.nip, pg.nama, pg.pangkat_gol, pg.jabatan, p.status, p.keterangan
                FROM presensi p
                JOIN pegawai pg ON p.nip = pg.nip
                WHERE strftime('%m', p.tanggal) = '{sel_bln}'
            """
            if sel_sek_rekap != "Semua Sekolah":
                query_rekap += f" AND pg.nama_sekolah = '{sel_sek_rekap}'"

            df_rekap = pd.read_sql_query(query_rekap, conn)
            st.dataframe(df_rekap, use_container_width=True)

            # Tombol Unduh Excel
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df_rekap.to_excel(writer, index=False, sheet_name='Rekap_Presensi')

            st.download_button(
                label="📥 Unduh Rekapitulasi Format Excel (.xlsx)",
                data=buffer_excel.getvalue(),
                file_name=f"Rekap_Presensi_{sel_sek_rekap}_Bulan_{sel_bln}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ----------------------------------------------------------------------
        # MENU: DATA PTK
        # ----------------------------------------------------------------------
        elif selected_menu == "Data PTK":
            st.header("👥 Kelola Data Tenaga Pendidik & Kependidikan")

            # Isolasi Data PTK berdasarkan Role
            if user['role'] == 'superadmin':
                df_ptk = pd.read_sql_query("SELECT nip, nama, nama_sekolah, pangkat_gol, jabatan, foto_uploaded FROM pegawai", conn)
            else:
                df_ptk = pd.read_sql_query(f"SELECT nip, nama, nama_sekolah, pangkat_gol, jabatan, foto_uploaded FROM pegawai WHERE nama_sekolah='{user['sekolah']}'", conn)

            st.dataframe(df_ptk, use_container_width=True)

            tab_tambah, tab_excel, tab_foto = st.tabs(["➕ Tambah/Edit Manual", "📁 Impor via Excel", "📸 Upload Foto Wajah Master"])

            # TAB 1: TAMBAH / EDIT MANUAL
            with tab_tambah:
                with st.form("form_ptk_manual"):
                    f_nip = st.text_input("NIP Pegawai")
                    f_nama = st.text_input("Nama Lengkap")
                    f_sek = st.text_input("Nama Sekolah", value=user['sekolah'] if user['role'] != 'superadmin' else "")
                    f_gol = st.text_input("Pangkat / Golongan")
                    f_jab = st.text_input("Jabatan")

                    if st.form_submit_button("Simpan Data Pegawai"):
                        c = conn.cursor()
                        c.execute("""
                            INSERT OR REPLACE INTO pegawai (nip, nama, nama_sekolah, pangkat_gol, jabatan)
                            VALUES (?, ?, ?, ?, ?)
                        """, (f_nip.strip(), f_nama.strip(), f_sek.strip(), f_gol.strip(), f_jab.strip()))
                        conn.commit()
                        st.success("Data Pegawai berhasil disimpan!")
                        st.rerun()

            # TAB 2: IMPOR EXCEL
            with tab_excel:
                st.write("Unduh contoh template excel terlebih dahulu untuk menyesuaikan format kolom.")
                
                # Sample Template Excel Download
                df_tpl = pd.DataFrame(columns=["nip", "nama", "nama_sekolah", "pangkat_gol", "jabatan"])
                tpl_buffer = io.BytesIO()
                with pd.ExcelWriter(tpl_buffer, engine='openpyxl') as writer:
                    df_tpl.to_excel(writer, index=False)

                st.download_button("📄 Unduh Template Excel Contoh", tpl_buffer.getvalue(), "Template_Data_PTK.xlsx")

                up_excel = st.file_uploader("Unggah File Excel PTK", type=["xlsx"])
                if up_excel:
                    df_upload = pd.read_excel(up_excel)
                    if user['role'] != 'superadmin':
                        df_upload['nama_sekolah'] = user['sekolah']

                    c = conn.cursor()
                    for _, r in df_upload.iterrows():
                        c.execute("""
                            INSERT OR REPLACE INTO pegawai (nip, nama, nama_sekolah, pangkat_gol, jabatan)
                            VALUES (?, ?, ?, ?, ?)
                        """, (str(r['nip']).strip(), str(r['nama']).strip(), str(r['nama_sekolah']).strip(), str(r['pangkat_gol']).strip(), str(r['jabatan']).strip()))
                    conn.commit()
                    st.success("Impor data dari Excel berhasil!")
                    st.rerun()

            # TAB 3: UPLOAD FOTO WAJAH MASTER
            with tab_foto:
                st.write("Pilih pegawai untuk mengunggah foto master (Format JPEG/JPG). Foto ini akan digunakan sebagai pembanding saat presensi.")
                
                if df_ptk.empty:
                    st.warning("Belum ada data pegawai.")
                else:
                    sel_nip = st.selectbox("Pilih NIP Pegawai", df_ptk['nip'].tolist())
                    peg_info = df_ptk[df_ptk['nip'] == sel_nip].iloc[0]

                    is_uploaded = peg_info['foto_uploaded']
                    bisa_upload = False

                    if user['role'] == 'superadmin':
                        bisa_upload = True
                        if is_uploaded == 1:
                            st.info("ℹ️ Mode Super Admin: Anda memiliki wewenang untuk mengganti foto master ini.")
                    elif is_uploaded == 0:
                        bisa_upload = True
                    else:
                        st.error("🔒 Foto master sudah diunggah sebelumnya. Admin Sekolah hanya dapat mengunggah foto 1 KALI. Hubungi Super Admin jika ingin mengganti foto.")

                    if bisa_upload:
                        file_jpg = st.file_uploader("Upload Foto Pasfoto JPEG Wajah", type=["jpg", "jpeg"])
                        if file_jpg:
                            bytes_img = file_jpg.read()
                            ok, vector, msg_vector = ekstrak_vector_wajah(bytes_img)

                            if ok:
                                c = conn.cursor()
                                vec_json = json.dumps(vector)
                                c.execute("UPDATE pegawai SET foto_vector=?, foto_uploaded=1 WHERE nip=?", (vec_json, sel_nip))
                                conn.commit()
                                st.success("✅ Foto Master & Vektor Wajah Berhasil Disimpan!")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg_vector}")

        # ----------------------------------------------------------------------
        # MENU: UPLOAD SURAT CUTI/SAKIT (SUPER ADMIN ONLY)
        # ----------------------------------------------------------------------
        elif selected_menu == "Upload Surat Cuti/Sakit":
            st.header("📄 Input Surat Cuti / Sakit / Tugas (Super Admin)")

            df_all_ptk = pd.read_sql_query("SELECT nip, nama, nama_sekolah FROM pegawai", conn)
            dict_ptk = {f"{r['nip']} - {r['nama']} ({r['nama_sekolah']})": r['nip'] for _, r in df_all_ptk.iterrows()}

            if not dict_ptk:
                st.warning("Data pegawai masih kosong.")
            else:
                sel_ptk_label = st.selectbox("Pilih Pegawai", list(dict_ptk.keys()))
                jns_surat = st.selectbox("Jenis Keterangan Presensi", ["Cuti", "Sakit", "Surat Tugas", "Izin"])

                col_dt1, col_dt2 = st.columns(2)
                tgl_m = col_dt1.date_input("Tanggal Mulai")
                tgl_s = col_dt2.date_input("Tanggal Selesai")

                file_surat = st.file_uploader("Unggah File Bukti Surat (PDF/JPG)", type=["pdf", "jpg", "jpeg", "png"])

                if st.button("Proses Input Surat Keterangan"):
                    if file_surat:
                        nip_target = dict_ptk[sel_ptk_label]
                        c = conn.cursor()
                        rng = pd.date_range(tgl_m, tgl_s)

                        for d in rng:
                            d_str = d.strftime("%Y-%m-%d")
                            c.execute("""
                                INSERT OR REPLACE INTO presensi (nip, tanggal, jam, status, lat, lon, keterangan)
                                VALUES (?, ?, '-', ?, 0.0, 0.0, ?)
                            """, (nip_target, d_str, jns_surat, f"Disetujui SuperAdmin: File {file_surat.name}"))
                        conn.commit()
                        st.success(f"Keterangan {jns_surat} berhasil dicatat dari {tgl_m} hingga {tgl_s}.")

        # ----------------------------------------------------------------------
        # MENU: TAMBAH AKUN ADMIN SEKOLAH (SUPER ADMIN ONLY)
        # ----------------------------------------------------------------------
        elif selected_menu == "Tambah Akun Admin Sekolah":
            st.header("🔐 Kelola Akun Admin Sekolah (Super Admin)")

            with st.form("form_add_admin"):
                st.subheader("Tambah Akun Admin Sekolah Baru")
                n_sek = st.text_input("Nama Sekolah Lengkap (Contoh: SMAN 1 MAKASSAR)")
                u_admin = st.text_input("Username Admin Sekolah")
                p_admin = st.text_input("Password Admin", type="password")

                if st.form_submit_button("Buat Akun Admin"):
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO admin (username, password, nama_sekolah, role) VALUES (?, ?, ?, 'admin_sekolah')",
                                  (u_admin.strip(), p_admin.strip(), n_sek.strip()))
                        conn.commit()
                        st.success(f"Akun Admin Sekolah untuk {n_sek} Berhasil Dibuat!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menambah akun admin: {e}")

            st.divider()
            st.subheader("Daftar Akun Admin Sekolah & Reset Password")
            df_adm = pd.read_sql_query("SELECT id, username, nama_sekolah FROM admin WHERE role='admin_sekolah'", conn)
            st.dataframe(df_adm, use_container_width=True)

            if not df_adm.empty:
                st.subheader("🔑 Reset Password Admin Sekolah")
                usr_reset = st.selectbox("Pilih User Admin Sekolah", df_adm['username'].tolist())
                pass_baru = st.text_input("Password Baru", type="password")

                if st.button("Reset Password Admin"):
                    if pass_baru:
                        c = conn.cursor()
                        c.execute("UPDATE admin SET password=? WHERE username=?", (pass_baru.strip(), usr_reset))
                        conn.commit()
                        st.success(f"Password akun admin '{usr_reset}' telah berhasil diperbarui!")