import sys
import subprocess
import threading
import os
import streamlit as st

st.set_page_config(
    page_title="YouTube Link → Live (Forced)",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 YouTube Link → Live Stream (FORCED MODE)")
st.warning(
    "Mode ini DOWNLOAD video YouTube dulu, lalu di-loop ke Live.\n"
    "BUKAN real-time YouTube Live source."
)

# ======================
# CHECK FFMPEG
# ======================
def check_dep():
    if not shutil.which("ffmpeg"):
        st.error("ffmpeg tidak tersedia")
        st.stop()

# ======================
# DOWNLOAD YOUTUBE
# ======================
def download_youtube(url, log):
    output_file = "temp_video.mp4"

    if os.path.exists(output_file):
        os.remove(output_file)

    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "-o", output_file,
        url
    ]

    log("Downloading YouTube video...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        log(line.strip())

    process.wait()

    if not os.path.exists(output_file):
        raise RuntimeError("Download gagal")

    return output_file

# ======================
# STREAM WITH FFMPEG
# ======================
def run_ffmpeg(video_path, stream_key, is_shorts, log):
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = "720:1280" if is_shorts else "1280:720"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-re",
        "-i", video_path,
        "-vf", f"scale={scale}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-keyint_min", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        output_url
    ]

    log("Menjalankan FFmpeg...")
    log(" ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        log(line.strip())

# ======================
# UI
# ======================
yt_url = st.text_input("🔗 Link YouTube", placeholder="https://youtu.be/xxxxx")
stream_key = st.text_input("🔑 Stream Key YouTube", type="password")
is_shorts = st.checkbox("Mode Shorts (720x1280)", value=False)

log_box = st.empty()
logs = []

def log(msg):
    logs.append(msg)
    log_box.text("\n".join(logs[-20:]))

if st.button("🔥 PAKSA LIVE"):
    if not yt_url or not stream_key:
        st.error("Link YouTube & Stream Key wajib diisi")
    else:
        try:
            video_file = download_youtube(yt_url, log)
            threading.Thread(
                target=run_ffmpeg,
                args=(video_file, stream_key, is_shorts, log),
                daemon=True
            ).start()
            st.success("Streaming dimulai (FORCED MODE)")
        except Exception as e:
            st.error(str(e))

if st.button("🛑 STOP"):
    os.system("pkill ffmpeg")
    if os.path.exists("temp_video.mp4"):
        os.remove("temp_video.mp4")
    st.warning("Streaming dihentikan")
