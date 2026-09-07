import streamlit as st
import streamlit.components.v1 as components
import os

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Sistem Absensi PTK",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Sembunyikan Header & Padding Bawaan Streamlit agar Antarmuka Tampil Penuh
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
        }
        iframe {
            width: 100% !important;
            border: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Mocking JS untuk 'google.script.run'
# Mencegah error Javascript saat tombol diklik di lingkungan Streamlit
JS_MOCK_SCRIPT = """
<script>
if (typeof google === 'undefined') {
    window.google = {
        script: {
            run: {
                withSuccessHandler: function(callback) {
                    return {
                        prosesLogin: function(u, p) {
                            setTimeout(() => callback({status: true, role: 'Super Admin', school: 'SMA Negeri 1'}), 400);
                        },
                        getStatusAbsenHariIni: function(s, r) {
                            setTimeout(() => callback([]), 300);
                        },
                        getPegawai: function(s, r) {
                            setTimeout(() => callback([
                                {id: "1", nip: "198501012010011001", nama: "Budi Santoso", sekolah: "SMA Negeri 1", pangkat: "III/c", jabatan: "Guru Matematika", statusFoto: "Belum Upload", foto: ""},
                                {id: "2", nip: "199002022015022002", nama: "Siti Rahma", sekolah: "SMA Negeri 1", pangkat: "III/b", jabatan: "Guru Bahasa Indonesia", statusFoto: "Belum Upload", foto: ""}
                            ]), 300);
                        },
                        simpanAbsen: function(data) {
                            setTimeout(() => callback({message: 'Presensi ' + data.jenis + ' berhasil disimpan!'}), 500);
                        },
                        getPengaturan: function() {
                            setTimeout(() => callback({masuk: '07:30', pulang: '14:00', koordinat: '-5.147665, 119.432731'}), 300);
                        },
                        simpanPengaturan: function(data) {
                            setTimeout(() => callback({message: 'Pengaturan berhasil disimpan!'}), 300);
                        },
                        tambahAdminSekolah: function(data) {
                            setTimeout(() => callback({message: 'Akun admin berhasil dibuat!'}), 300);
                        },
                        simpanSurat: function(data) {
                            setTimeout(() => callback({message: 'Surat izin berhasil diunggah!'}), 300);
                        },
                        simpanPegawai: function(data, role) {
                            setTimeout(() => callback({message: 'Data pegawai berhasil ditambahkan!'}), 300);
                        },
                        uploadFotoPegawai: function(id, img, role) {
                            setTimeout(() => callback({message: 'Foto pegawai berhasil diunggah!'}), 300);
                        }
                    };
                }
            }
        }
    };
}
</script>
"""

# 4. Baca dan Tampilkan File HTML
HTML_FILE_PATH = "frontend_antarmuka.html"

if os.path.exists(HTML_FILE_PATH):
    try:
        with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Sisipkan JS Mock ke dalam HTML sebelum tag </head>
        if "</head>" in html_content:
            html_content = html_content.replace("</head>", f"{JS_MOCK_SCRIPT}\n</head>")
        else:
            html_content = JS_MOCK_SCRIPT + html_content

        # Render HTML aman di dalam Iframe
        components.html(html_content, height=950, scrolling=True)

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat membaca file HTML: {e}")
else:
    st.error(f"❌ File **`{HTML_FILE_PATH}`** tidak ditemukan!")
    st.warning("""
    **Langkah Perbaikan:**
    1. Pastikan file `frontend_antarmuka.html` berada di folder/direktori yang **sama** dengan file `app.py`.
    2. Pastikan file `frontend_antarmuka.html` sudah di-push / diunggah ke repositori GitHub Anda.
    """)
