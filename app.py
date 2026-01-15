import sys
import subprocess
import threading
import os
import shutil
import streamlit as st

# =========================
# STREAMLIT CONFIG
# =========================
st.set_page_config(
    page_title="🔥 YouTube Link → Live (Forced)",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 YouTube Link → Live Stream (FORCED MODE)")
st.warning(
    "Mode ini:\n"
    "- Download video YouTube dulu\n"
    "- Disimpan jadi file lokal\n"
    "- Di-loop ke YouTube Live\n\n"
    "❌ BUKAN real-time YouTube live source"
)

# =========================
# CHECK DEPENDENCY
# =========================
def check_dep():
    if not shutil.which("ffmpeg"):
        st.error("❌ ffmpeg tidak tersedia")
        st.stop()
    if not shutil.which("yt-dlp"):
        st.error("❌ yt-dlp tidak tersedia")
        st.stop()

check_dep()

# =========================
# LOGGER
# =========================
log_box = st.empty()
logs = []

def log(msg):
    logs.append(msg)
    log_box.text("\n".join(logs[-25:]))

# =========================
# DOWNLOAD YOUTUBE (ANTI 403)
# =========================
def download_youtube(url):
    output_file = "temp_video.mp4"

    if os.path.exists(output_file):
        os.remove(output_file)

    cmd = [
        "yt-dlp",
        "--no-check-certificate",
        "--force-ipv4",
        "--user-agent", "Mozilla/5.0 (Linux; Android 11)",
        "--extractor-args", "youtube:player_client=android",
        "--merge-output-format", "mp4",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "-o", output_file,
        url
    ]

    log("📥 Downloading YouTube video (forced android client)...")
    log("CMD: " + " ".join(cmd))

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
        raise RuntimeError("❌ Download gagal (YouTube 403 / SABR block)")

    return output_file

# =========================
# FFMPEG STREAM
# =========================
def run_ffmpeg(video_path, stream_key, is_shorts):
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = "720:1280" if is_shorts else "1280:720"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-fflags", "+genpts",
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
        "-flvflags", "no_duration_filesize",
        output_url
    ]

    log("🚀 Starting FFmpeg streaming...")
    log("CMD: " + " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        log(line.strip())

# =========================
# UI INPUT
# =========================
yt_url = st.text_input(
    "🔗 Link YouTube",
    placeholder="https://youtu.be/xxxxx"
)

stream_key = st.text_input(
    "🔑 YouTube Stream Key",
    type="password"
)

is_shorts = st.checkbox("📱 Mode Shorts (720x1280)", value=False)

# =========================
# BUTTON ACTIONS
# =========================
if st.button("🔥 PAKSA LIVE"):
    if not yt_url or not stream_key:
        st.error("❌ Link YouTube dan Stream Key wajib diisi")
    else:
        try:
            video_file = download_youtube(yt_url)
            threading.Thread(
                target=run_ffmpeg,
                args=(video_file, stream_key, is_shorts),
                daemon=True
            ).start()
            st.success("✅ Streaming dimulai (FORCED MODE)")
        except Exception as e:
            st.error(str(e))

if st.button("🛑 STOP"):
    os.system("pkill ffmpeg")
    if os.path.exists("temp_video.mp4"):
        os.remove("temp_video.mp4")
    st.warning("⚠️ Streaming dihentikan")

# =========================
# SHOW LOG
# =========================
log_box.text("\n".join(logs[-25:]))
