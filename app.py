#!/usr/bin/env python3
import subprocess
import threading
import shutil
import sys
import streamlit as st

# ==============================
# CHECK DEPENDENCY
# ==============================
def check_dep():
    if not shutil.which("ffmpeg"):
        st.error("ffmpeg tidak ditemukan")
        st.stop()
    if not shutil.which("yt-dlp"):
        st.error("yt-dlp tidak ditemukan")
        st.stop()

# ==============================
# PLATFORM RTMP BASE
# ==============================
RTMP_BASE = {
    "youtube": "rtmp://a.rtmp.youtube.com/live2/",
    "facebook": "rtmp://live-api-s.facebook.com:80/rtmp/",
    "tiktok": "rtmp://live.tiktok.com/live/"
}

# ==============================
# PRESETS
# ==============================
PRESETS = {
    "youtube": {
        "video_bitrate": "4500k",
        "audio_bitrate": "128k",
        "fps": 30,
        "resolution": "1280x720"
    },
    "facebook": {
        "video_bitrate": "4000k",
        "audio_bitrate": "128k",
        "fps": 30,
        "resolution": "1280x720"
    },
    "tiktok": {
        "video_bitrate": "3000k",
        "audio_bitrate": "128k",
        "fps": 30,
        "resolution": "720x1280"
    }
}

# ==============================
# GET YOUTUBE STREAM URL
# ==============================
def get_youtube_stream(url):
    cmd = ["yt-dlp", "-f", "best", "-g", url]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        st.error("Gagal mengambil stream YouTube")
        st.code(result.stderr)
        st.stop()

    return result.stdout.strip().splitlines()[0]

# ==============================
# STREAM FUNCTION
# ==============================
def start_stream(
    input_url,
    rtmp_url,
    preset,
    video_bitrate,
    audio_bitrate,
    fps,
    resolution,
    log_box
):
    cmd = [
        "ffmpeg",
        "-re",
        "-i", input_url,
        "-vf", f"scale={resolution}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", video_bitrate,
        "-maxrate", video_bitrate,
        "-bufsize", "2M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-f", "flv",
        rtmp_url
    ]

    logs = []

    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        text=True
    )

    def monitor():
        for line in process.stderr:
            if "frame=" in line or "time=" in line:
                logs.append(line.strip())
                log_box.code("\n".join(logs[-20:]))

    threading.Thread(target=monitor, daemon=True).start()
    process.wait()

# ==============================
# STREAMLIT UI (CONVERTED MAIN)
# ==============================
st.set_page_config(page_title="YouTube Restreamer", layout="centered")
st.title("YouTube → Live Stream (Streamlit)")

st.warning(
    "⚠️ Aplikasi ini HARUS dijalankan di Termux / VPS.\n\n"
    "Streamlit Cloud tidak mendukung RTMP push."
)

check_dep()

platform = st.selectbox(
    "Pilih Platform",
    ["youtube", "facebook", "tiktok", "custom"]
)

yt_url = st.text_input("Link YouTube")

if platform == "custom":
    rtmp_base = st.text_input("RTMP Base (tanpa stream key)")
else:
    rtmp_base = RTMP_BASE[platform]

stream_key = st.text_input("Stream Key", type="password")

log_box = st.empty()

if st.button("▶ MULAI STREAM"):
    if not yt_url or not stream_key:
        st.error("Link YouTube dan Stream Key wajib diisi")
    else:
        stream_url = get_youtube_stream(yt_url)

        final_rtmp = rtmp_base.rstrip("/") + "/" + stream_key

        if platform in PRESETS:
            p = PRESETS[platform]
            start_stream(
                stream_url,
                final_rtmp,
                platform,
                p["video_bitrate"],
                p["audio_bitrate"],
                p["fps"],
                p["resolution"],
                log_box
            )
        else:
            video_bitrate = st.text_input("Video Bitrate", "2500k")
            audio_bitrate = st.text_input("Audio Bitrate", "128k")
            fps = st.number_input("FPS", 1, 60, 30)
            resolution = st.text_input("Resolusi", "1280x720")

            start_stream(
                stream_url,
                final_rtmp,
                "custom",
                video_bitrate,
                audio_bitrate,
                fps,
                resolution,
                log_box
            )
