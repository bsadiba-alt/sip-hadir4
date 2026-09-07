from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Data simulasi (In-Memory Database)
DATA_PEGAMAI = [
    {"id": "1", "nip": "198501012010011001", "nama": "Budi Santoso", "sekolah": "SMA Negeri 1", "pangkat": "III/c", "jabatan": "Guru Matematika", "statusFoto": "Belum Upload", "foto": ""},
    {"id": "2", "nip": "199002022015022002", "nama": "Siti Rahma", "sekolah": "SMA Negeri 1", "pangkat": "III/b", "jabatan": "Guru Bahasa Indonesia", "statusFoto": "Belum Upload", "foto": ""}
]

DATA_ABSEN = []
PENGATURAN = {"masuk": "07:30", "pulang": "14:00", "koordinat": "-5.147665, 119.432731"}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    u, p = data.get('username'), data.get('password')
    
    if u == "admin" and p == "admin123":
        return jsonify({"status": True, "role": "Super Admin", "school": "Semua Sekolah"})
    elif u == "guru" and p == "guru123":
        return jsonify({"status": True, "role": "Admin Sekolah", "school": "SMA Negeri 1"})
    return jsonify({"status": False, "message": "Username atau Password salah!"})

@app.route('/api/pegawai', methods=['GET'])
def get_pegawai():
    return jsonify(DATA_PEGAMAI)

@app.route('/api/absen', methods=['POST'])
def simpan_absen():
    data = request.get_json()
    DATA_ABSEN.append({
        "waktu": "2026-09-07T08:00:00.000Z",
        "nama": data.get("nama"),
        "sekolah": data.get("sekolah"),
        "status": data.get("jenis"),
        "foto": data.get("foto")
    })
    return jsonify({"status": True, "message": f"Absen {data.get('jenis')} Berhasil!"})

@app.route('/api/status-absen', methods=['GET'])
def get_status_absen():
    return jsonify(DATA_ABSEN)

@app.route('/api/pengaturan', methods=['GET', 'POST'])
def handle_pengaturan():
    global PENGATURAN
    if request.method == 'POST':
        PENGATURAN = request.get_json()
        return jsonify({"status": True, "message": "Pengaturan berhasil disimpan!"})
    return jsonify(PENGATURAN)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
