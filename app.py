import os
import subprocess
import threading
import streamlit as st

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="YouTube Live Uploader",
    page_icon="📡",
    layout="wide"
)

# =========================
# HEADER
# =========================
st.markdown("""
<style>
.main-title {
    font-size: 36px;
    font-weight: 800;
}
.card {
    padding: 20px;
    border-radius: 15px;
    background: #0f172a;
    color: white;
}
.log-box {
    background: #020617;
    padding: 15px;
    border-radius: 10px;
    font-family: monospace;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📡 YouTube Live Streaming (Upload Mode)</div>', unsafe_allow_html=True)
st.caption("Upload video → Loop → YouTube Live (Cloud Safe)")

st.divider()

# =========================
# SESSION STATE
# =========================
if "logs" not in st.session_state:
    st.session_state.logs = []

def log(msg):
    st.session_state.logs.append(msg)
    log_placeholder.markdown(
        '<div class="log-box">' +
        "<br>".join(st.session_state.logs[-25:]) +
        '</div>',
        unsafe_allow_html=True
    )

# =========================
# LAYOUT
# =========================
left, right = st.columns([1, 1])

with left:
    st.markdown("### 🎞️ Upload Video")
    uploaded = st.file_uploader(
        "Format MP4 / FLV (H264 + AAC)",
        type=["mp4", "flv"]
    )

    if uploaded:
        video_path = uploaded.name
        with open(video_path, "wb") as f:
            f.write(uploaded.read())
        st.success("✅ Video siap digunakan")
    else:
        video_path = None

    st.markdown("### 🔑 Stream Key")
    stream_key = st.text_input(
        "YouTube Stream Key",
        type="password",
        placeholder="xxxx-xxxx-xxxx-xxxx"
    )

    st.markdown("### 📐 Mode Video")
    mode = st.radio(
        "Pilih format:",
        ["Landscape (16:9)", "Shorts (9:16)"]
    )

with right:
    st.markdown("### 📊 Status Streaming")
    log_placeholder = st.empty()

# =========================
# FFMPEG FUNCTION
# =========================
def run_ffmpeg(video, key, is_shorts):
    scale = "720:1280" if is_shorts else "1280:720"
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{key}"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-re",
        "-i", video,
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

    log("🚀 Streaming dimulai...")
    log(" ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        log(line.strip())

# =========================
# CONTROLS
# =========================
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ MULAI LIVE", use_container_width=True):
        if not video_path or not stream_key:
            st.error("Video dan Stream Key wajib diisi")
        else:
            threading.Thread(
                target=run_ffmpeg,
                args=(video_path, stream_key, mode.startswith("Shorts")),
                daemon=True
            ).start()
            st.success("Live dimulai")

with col2:
    if st.button("🛑 STOP LIVE", use_container_width=True):
        os.system("pkill ffmpeg")
        st.warning("Streaming dihentikan")
