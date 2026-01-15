import streamlit as st
import subprocess
import threading
import uuid
import re

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Multi Live Streamer (Google Drive FIX)",
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
small { color:#94a3b8; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📡 Multi Live Streaming (Google Drive)</div>', unsafe_allow_html=True)
st.caption("FIX Thread + SessionState (Anti Error)")
st.divider()

# ==================================================
# SESSION STATE INIT (WAJIB PALING ATAS)
# ==================================================
if "streams" not in st.session_state:
    st.session_state.streams = {}

# ==================================================
# GOOGLE DRIVE PARSER
# ==================================================
def gdrive_direct(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
    return url

# ==================================================
# FFMPEG THREAD (TIDAK SENTUH STREAMLIT)
# ==================================================
def ffmpeg_worker(cmd):
    subprocess.Popen(cmd)

# ==================================================
# ADD STREAM FORM
# ==================================================
st.markdown("## ➕ Tambah Stream")

with st.form("add"):
    gdrive = st.text_input("Google Drive Link")
    key = st.text_input("YouTube Stream Key", type="password")
    mode = st.radio("Mode", ["Landscape", "Shorts"])
    submit = st.form_submit_button("Tambah")

    if submit:
        if not gdrive or not key:
            st.error("Link & Stream Key wajib")
        else:
            sid = str(uuid.uuid4())[:8]
            st.session_state.streams[sid] = {
                "url": gdrive_direct(gdrive),
                "key": key,
                "shorts": mode == "Shorts",
                "process": None
            }
            st.success(f"Stream {sid} ditambahkan")

st.divider()

# ==================================================
# STREAM LIST
# ==================================================
st.markdown("## 🎬 Daftar Stream")

for sid, data in list(st.session_state.streams.items()):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### ID: `{sid}`")
        st.markdown(f"<small>{data['url']}</small>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        scale = "720:1280" if data["shorts"] else "1280:720"
        rtmp = f"rtmp://a.rtmp.youtube.com/live2/{data['key']}"

        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", data["url"],
            "-vf", f"scale={scale}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-b:v", "3000k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-g", "60",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            rtmp
        ]

        with col1:
            if st.button(f"▶ START {sid}"):
                if data["process"] is None:
                    p = subprocess.Popen(cmd)
                    data["process"] = p
                    st.success("Streaming dimulai")
                else:
                    st.warning("Sudah berjalan")

        with col2:
            if st.button(f"🛑 STOP {sid}"):
                if data["process"]:
                    data["process"].terminate()
                    data["process"] = None
                    st.warning("Streaming dihentikan")

        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
