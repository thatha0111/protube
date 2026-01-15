import streamlit as st
import requests
import re

# ==================================================
# CONFIG PALING ATAS
# ==================================================
st.set_page_config(
    page_title="Multi Live Streamer (Google Drive Mode)",
    page_icon="📡",
    layout="wide"
)

import subprocess
import threading
import uuid

# ==================================================
# FUNGSI UNTUK KONVERSI GOOGLE DRIVE LINK
# ==================================================
def convert_google_drive_link(gdrive_url):
    """
    Konversi Google Drive share link menjadi direct download link
    """
    try:
        # Ekstrak file ID dari URL Google Drive
        file_id = None
        
        # Pattern 1: https://drive.google.com/file/d/FILE_ID/view
        pattern1 = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)'
        match1 = re.search(pattern1, gdrive_url)
        
        # Pattern 2: https://drive.google.com/open?id=FILE_ID
        pattern2 = r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
        match2 = re.search(pattern2, gdrive_url)
        
        if match1:
            file_id = match1.group(1)
        elif match2:
            file_id = match2.group(1)
        
        if not file_id:
            return None, "Tidak dapat menemukan File ID dalam URL"
        
        # Coba beberapa format direct link
        direct_links = [
            f"https://drive.google.com/uc?export=download&id={file_id}",
            f"https://docs.google.com/uc?export=download&id={file_id}",
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        ]
        
        # Coba setiap link sampai dapat yang berhasil
        for link in direct_links:
            try:
                # Cek HEAD request terlebih dahulu
                response = requests.head(link, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    return link, None
            except:
                continue
        
        # Jika semua gagal, return link pertama dengan confirm parameter
        return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t", None
        
    except Exception as e:
        return None, f"Error: {str(e)}"

# ==================================================
# FUNGSI UNTUK MENDAPATKAN UKURAN FILE
# ==================================================
def get_file_size(url):
    """Dapatkan ukuran file dari URL"""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        if 'content-length' in response.headers:
            size_bytes = int(response.headers['content-length'])
            # Konversi ke MB
            size_mb = size_bytes / (1024 * 1024)
            return size_mb
        return None
    except:
        return None

# ==================================================
# STYLE
# ==================================================
st.markdown("""
<style>
.title { font-size:36px; font-weight:800; }
.card {
  background:#0f172a;
  padding:20px;
  border-radius:15px;
  color:white;
  margin-bottom:20px;
}
.log {
  background:#020617;
  padding:10px;
  border-radius:10px;
  font-family:monospace;
  font-size:12px;
  max-height:220px;
  overflow-y:auto;
}
.info-box {
  background:#0c4a6e;
  padding:15px;
  border-radius:10px;
  margin:10px 0;
}
small { color:#94a3b8; }
.stButton > button {
  width: 100%;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📡 Multi Live Streaming (Google Drive Mode)</div>', unsafe_allow_html=True)
st.caption("Masukkan link Google Drive video → otomatis konversi ke direct link → stream ke YouTube Live")
st.divider()

# ==================================================
# INFORMASI
# ==================================================
with st.expander("📋 Cara Menggunakan", expanded=True):
    st.markdown("""
    1. **Salin link Google Drive** video Anda (format: `https://drive.google.com/file/d/...`)
    2. **Tempel link** di kolom input di bawah
    3. Sistem akan **otomatis konversi** ke direct download link
    4. Masukkan **YouTube Stream Key**
    5. Pilih mode video (Landscape atau Shorts)
    6. Klik **Tambah Stream**
    7. Klik **START** untuk mulai streaming
    
    **Catatan:** Pastikan video di Google Drive sudah di-share dengan akses "Anyone with the link"
    """)

# ==================================================
# SESSION STATE
# ==================================================
if "streams" not in st.session_state:
    st.session_state.streams = {}

# ==================================================
# FFMPEG RUNNER
# ==================================================
def run_ffmpeg(stream_id, video_url, stream_key, is_shorts):
    scale = "720:1280" if is_shorts else "1280:720"
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    # Konfigurasi untuk video besar (buffer yang lebih besar)
    cmd = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", video_url,
        "-vf", f"scale={scale}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "3000k",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-g", "60",
        "-keyint_min", "60",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        rtmp_url
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    st.session_state.streams[stream_id]["process"] = proc

    for line in iter(proc.stdout.readline, ''):
        if line:
            logs = st.session_state.streams[stream_id]["logs"]
            logs.append(line.strip())
            # Simpan hanya 50 log terakhir
            if len(logs) > 50:
                logs.pop(0)
            st.session_state.streams[stream_id]["logs"] = logs

# ==================================================
# FORM TAMBAH STREAM
# ==================================================
st.markdown("## ➕ Tambah Stream Baru")

with st.form("add_stream"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        gdrive_url = st.text_input(
            "Link Google Drive Video Anda",
            placeholder="https://drive.google.com/file/d/1NmTXyql_3DD4Ow-11dbGkgvUUf9_o150/view?usp=drivesdk",
            value="https://drive.google.com/file/d/1NmTXyql_3DD4Ow-11dbGkgvUUf9_o150/view?usp=drivesdk"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        convert_btn = st.form_submit_button("🔗 Konversi ke Direct Link")
    
    if convert_btn and gdrive_url:
        with st.spinner("Mengonversi link Google Drive..."):
            direct_link, error = convert_google_drive_link(gdrive_url)
            if direct_link:
                st.session_state.converted_link = direct_link
                st.success("✅ Link berhasil dikonversi!")
                
                # Cek ukuran file
                file_size = get_file_size(direct_link)
                if file_size:
                    st.info(f"📊 Ukuran video: {file_size:.2f} MB")
                else:
                    st.info("📊 Ukuran video: Tidak dapat mendeteksi")
            else:
                st.error(f"❌ Gagal mengonversi: {error}")
    
    # Tampilkan direct link jika sudah dikonversi
    if "converted_link" in st.session_state:
        st.code(f"Direct Link: {st.session_state.converted_link}", language="bash")
        video_url = st.session_state.converted_link
    else:
        video_url = ""
    
    stream_key = st.text_input(
        "YouTube Stream Key",
        type="password",
        placeholder="Masukkan stream key dari YouTube Studio"
    )
    
    mode = st.radio(
        "Mode Video",
        ["Landscape (16:9) - 1280x720", "Shorts/Vertical (9:16) - 720x1280"],
        horizontal=True
    )
    
    submit = st.form_submit_button("🚀 Tambah Stream")

    if submit:
        if not gdrive_url or not stream_key:
            st.error("❌ Link Google Drive dan Stream Key wajib diisi")
        else:
            # Konversi link jika belum dikonversi
            if "converted_link" not in st.session_state:
                with st.spinner("Mengonversi link..."):
                    direct_link, error = convert_google_drive_link(gdrive_url)
                    if direct_link:
                        video_url = direct_link
                        st.session_state.converted_link = direct_link
                    else:
                        st.error(f"❌ Gagal mengonversi link: {error}")
                        st.stop()
            else:
                video_url = st.session_state.converted_link
            
            sid = str(uuid.uuid4())[:8]
            
            st.session_state.streams[sid] = {
                "video_url": video_url,
                "original_gdrive": gdrive_url,
                "key": stream_key,
                "shorts": "Shorts" in mode,
                "process": None,
                "logs": []
            }
            
            st.success(f"✅ Stream `{sid}` berhasil ditambahkan")
            st.balloons()

st.divider()

# ==================================================
# DAFTAR STREAM
# ==================================================
st.markdown("## 🎬 Daftar Streaming Aktif")

if not st.session_state.streams:
    st.info("📭 Belum ada stream yang ditambahkan. Tambah stream baru di atas.")
else:
    for sid, data in list(st.session_state.streams.items()):
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            col_header1, col_header2 = st.columns([3, 1])
            
            with col_header1:
                st.markdown(f"### 📹 Stream ID: `{sid}`")
                st.markdown(f"<small>🔗 Google Drive: {data['original_gdrive'][:50]}...</small>", unsafe_allow_html=True)
                st.markdown(f"<small>📥 Direct Link: {data['video_url'][:50]}...</small>", unsafe_allow_html=True)
                st.markdown(f"<small>📐 Mode: {'Shorts/Vertical (9:16)' if data['shorts'] else 'Landscape (16:9)'}</small>", unsafe_allow_html=True)
            
            with col_header2:
                status = "🔴 STOPPED" if data["process"] is None else "🟢 LIVE"
                st.markdown(f"### {status}")
            
            st.divider()
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button(f"▶ START {sid}", key=f"start_{sid}", type="primary"):
                    if data["process"] is None:
                        t = threading.Thread(
                            target=run_ffmpeg,
                            args=(sid, data["video_url"], data["key"], data["shorts"]),
                            daemon=True
                        )
                        t.start()
                        st.success("🎬 Streaming dimulai! Periksa log di bawah.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Stream sudah berjalan")
            
            with col2:
                if st.button(f"🛑 STOP {sid}", key=f"stop_{sid}", type="secondary"):
                    if data["process"]:
                        data["process"].terminate()
                        data["process"] = None
                        st.warning("⏹️ Streaming dihentikan")
                        st.rerun()
            
            with col3:
                if st.button(f"🗑️ HAPUS {sid}", key=f"remove_{sid}"):
                    if data["process"]:
                        data["process"].terminate()
                    del st.session_state.streams[sid]
                    st.warning("🗑️ Stream dihapus")
                    st.rerun()
            
            # Tampilkan logs
            if data["logs"]:
                st.markdown("**📝 Live Logs:**")
                log_text = "\n".join(data["logs"][-20:])  # Tampilkan 20 log terakhir
                st.markdown(
                    f'<div class="log">{log_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.caption("Log akan muncul setelah stream dimulai...")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b;">
    <small>Multi Live Streaming Tool • Mendukung video besar dari Google Drive • Streamlit + FFmpeg</small>
</div>
""", unsafe_allow_html=True)
