import streamlit as st

# ==================================================
# KONFIGURASI WAJIB (PALING ATAS)
# ==================================================
st.config.set_option("server.maxUploadSize", 1536)  # 1.5 GB

st.set_page_config(
    page_title="Multi Live Streamer",
    page_icon="📡",
    layout="wide"
)

import os
import subprocess
import threading
import uuid

# ==================================================
# STYLE UI
# ==================================================
st.markdown("""
<style>
.title {
    font-size: 34px;
    font-weight: 800;
}
.card {
    background: #0f172a;
    padding: 20px;
    border-radius: 14px;
    color: white;
    margin-bottom: 20px;
}
.log {
    background: #020617;
    padding: 10px;
    border-radius: 10px;
    font-family: monospace;
    font-size: 12px;
    max-height: 220px;
    overflow-y: auto;
}
small {
    color: #94a3b8;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📡 Multi Live Streaming (Stable Upload)</div>', unsafe_allow_html=True)
st.caption("Upload video → stream key beda → bisa jalan bersamaan (Streamlit Cloud friendly)")
st.divider()

# ==================================================
# SESSION STATE
# ==================================================
if "streams" not in st.session_state:
    st.session_state.streams = {}

# ==================================================
# FFMPEG RUNNER
# ==================================================
def run_ffmpeg(stream_id, video_path, stream_key, is_shorts):
    scale = "720:1280" if is_shorts else "1280:720"
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-re",
        "-i", video_path,
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
        st.session_state.streams[stream_id]["logs"] = logs[-40:]

# ==================================================
# FORM TAMBAH STREAM
# ==================================================
st.markdown("## ➕ Tambah Stream Baru")

with st.form("add_stream"):
    uploaded = st.file_uploader(
        "Upload Video (MP4 / FLV – maks ±1.5GB)",
        type=["mp4", "flv"],
        accept_multiple_files=False
    )

    stream_key = st.text_input("Stream Key YouTube", type="password")

    mode = st.radio("Mode Video", ["Landscape (16:9)", "Shorts (9:16)"])

    submit = st.form_submit_button("Tambah Stream")

    if submit:
        if uploaded is None or not stream_key:
            st.error("❌ Video dan Stream Key wajib diisi")
        else:
            size_mb = uploaded.size / 1024 / 1024

            if size_mb > 1536:
                st.error("❌ File terlalu besar (maks ±1.5GB)")
            else:
                sid = str(uuid.uuid4())[:8]
                filename = f"{sid}_{uploaded.name}"

                with open(filename, "wb") as f:
                    f.write(uploaded.read())

                st.session_state.streams[sid] = {
                    "video": filename,
                    "key": stream_key,
                    "shorts": mode.startswith("Shorts"),
                    "process": None,
                    "logs": []
                }

                st.success(f"✅ Stream `{sid}` ditambahkan ({size_mb:.2f} MB)")

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
            st.markdown(f"<small>📁 File: {data['video']}</small>", unsafe_allow_html=True)
            st.markdown(f"<small>📐 Mode: {'Shorts' if data['shorts'] else 'Landscape'}</small>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"▶ START {sid}", key=f"start_{sid}"):
                    if data["process"] is None:
                        t = threading.Thread(
                            target=run_ffmpeg,
                            args=(sid, data["video"], data["key"], data["shorts"]),
                            daemon=True
                        )
                        t.start()
                        st.success("Streaming dimulai")
                    else:
                        st.warning("Stream sudah berjalan")

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
