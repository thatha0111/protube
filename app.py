import streamlit as st
import subprocess
import threading
import uuid
import re

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Multi Live Streamer (Google Drive Mode)",
    page_icon="📡",
    layout="wide"
)

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
small { color:#94a3b8; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📡 Multi Live Streaming (Google Drive)</div>', unsafe_allow_html=True)
st.caption("Masukkan link Google Drive → otomatis stream ke YouTube Live")
st.divider()

# ==================================================
# SESSION STATE
# ==================================================
if "streams" not in st.session_state:
    st.session_state.streams = {}

# ==================================================
# GOOGLE DRIVE PARSER
# ==================================================
def convert_gdrive_to_direct(url):
    """
    Convert Google Drive share link to direct download URL
    """
    patterns = [
        r"https://drive.google.com/file/d/([a-zA-Z0-9_-]+)",
        r"https://drive.google.com/open\?id=([a-zA-Z0-9_-]+)",
        r"https://drive.google.com/uc\?id=([a-zA-Z0-9_-]+)"
    ]

    for p in patterns:
        match = re.search(p, url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url  # fallback kalau bukan gdrive

# ==================================================
# FFMPEG RUNNER
# ==================================================
def run_ffmpeg(stream_id, video_url, stream_key, is_shorts):
    scale = "720:1280" if is_shorts else "1280:720"
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

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
        text=True
    )

    st.session_state.streams[stream_id]["process"] = proc

    for line in proc.stdout:
        logs = st.session_state.streams[stream_id]["logs"]
        logs.append(line.strip())
        st.session_state.streams[stream_id]["logs"] = logs[-50:]

# ==================================================
# FORM TAMBAH STREAM
# ==================================================
st.markdown("## ➕ Tambah Stream")

with st.form("add_stream"):
    gdrive_url = st.text_input(
        "Google Drive Video Link",
        placeholder="https://drive.google.com/file/d/xxxxx/view"
    )

    stream_key = st.text_input(
        "YouTube Stream Key",
        type="password"
    )

    mode = st.radio(
        "Mode Video",
        ["Landscape (16:9)", "Shorts (9:16)"]
    )

    submit = st.form_submit_button("Tambah Stream")

    if submit:
        if not gdrive_url or not stream_key:
            st.error("❌ Link Google Drive dan Stream Key wajib diisi")
        else:
            direct_url = convert_gdrive_to_direct(gdrive_url)
            sid = str(uuid.uuid4())[:8]

            st.session_state.streams[sid] = {
                "video_url": direct_url,
                "key": stream_key,
                "shorts": mode.startswith("Shorts"),
                "process": None,
                "logs": []
            }

            st.success("✅ Stream berhasil ditambahkan")
            st.code(direct_url)

st.divider()

# ==================================================
# DAFTAR STREAM
# ==================================================
st.markdown("## 🎬 Daftar Streaming")

if not st.session_state.streams:
    st.info("Belum ada stream.")
else:
    for sid, data in list(st.session_state.streams.items()):
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.markdown(f"### Stream ID: `{sid}`")
            st.markdown(f"<small>🔗 Source: {data['video_url']}</small>", unsafe_allow_html=True)
            st.markdown(f"<small>📐 Mode: {'Shorts' if data['shorts'] else 'Landscape'}</small>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"▶ START {sid}", key=f"start_{sid}"):
                    if data["process"] is None:
                        t = threading.Thread(
                            target=run_ffmpeg,
                            args=(sid, data["video_url"], data["key"], data["shorts"]),
                            daemon=True
                        )
                        t.start()
                        st.success("Streaming dimulai")

            with col2:
                if st.button(f"🛑 STOP {sid}", key=f"stop_{sid}"):
                    if data["process"]:
                        data["process"].terminate()
                        data["process"] = None
                        st.warning("Streaming dihentikan")

            if data["logs"]:
                st.markdown(
                    '<div class="log">' +
                    "<br>".join(data["logs"]) +
                    '</div>',
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
