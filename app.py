import streamlit as st
import subprocess
import threading
import uuid
import re
import requests
import os
import time

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="GDrive PRO → YouTube Live",
    page_icon="📡",
    layout="wide"
)

DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==================================================
# SESSION STATE
# ==================================================
if "jobs" not in st.session_state:
    st.session_state.jobs = {}

# ==================================================
# GOOGLE DRIVE DOWNLOAD (PRO + RESUME)
# ==================================================
def download_gdrive(file_id, output_path, job_id):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    headers = {}
    downloaded = 0

    if os.path.exists(output_path):
        downloaded = os.path.getsize(output_path)
        headers["Range"] = f"bytes={downloaded}-"

    response = session.get(URL, params={"id": file_id}, headers=headers, stream=True)
    token = None

    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            token = v

    if token:
        response = session.get(
            URL,
            params={"id": file_id, "confirm": token},
            headers=headers,
            stream=True
        )

    total = int(response.headers.get("Content-Length", 0)) + downloaded

    mode = "ab" if downloaded else "wb"
    with open(output_path, mode) as f:
        for chunk in response.iter_content(1024 * 256):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                st.session_state.jobs[job_id]["progress"] = downloaded / total

    st.session_state.jobs[job_id]["download_done"] = True

# ==================================================
# FFMPEG AUTO RECONNECT
# ==================================================
def ffmpeg_loop(video_path, stream_key, shorts, job_id):
    scale = "720:1280" if shorts else "1280:720"
    rtmp = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    while st.session_state.jobs[job_id]["active"]:
        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", video_path,
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

        p = subprocess.Popen(cmd)
        st.session_state.jobs[job_id]["ffmpeg"] = p
        p.wait()
        time.sleep(3)

# ==================================================
# UI
# ==================================================
st.title("📡 Google Drive → YouTube Live (PRO VERSION)")
st.caption("Download besar • Resume • Multi Stream • Auto Reconnect")
st.divider()

with st.form("add"):
    gdrive = st.text_input("Google Drive Video Link")
    key = st.text_input("YouTube Stream Key", type="password")
    mode = st.radio("Mode Video", ["Landscape", "Shorts"])
    submit = st.form_submit_button("ADD STREAM")

    if submit:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", gdrive)
        if not match:
            st.error("Link Google Drive tidak valid")
        else:
            jid = str(uuid.uuid4())[:8]
            file_id = match.group(1)
            path = os.path.join(DOWNLOAD_DIR, f"{jid}.mp4")

            st.session_state.jobs[jid] = {
                "file_id": file_id,
                "path": path,
                "key": key,
                "shorts": mode == "Shorts",
                "progress": 0.0,
                "download_done": False,
                "active": True,
                "ffmpeg": None
            }

            threading.Thread(
                target=download_gdrive,
                args=(file_id, path, jid),
                daemon=True
            ).start()

            st.success(f"Job {jid} ditambahkan")

st.divider()

# ==================================================
# JOB LIST
# ==================================================
for jid, job in list(st.session_state.jobs.items()):
    with st.container():
        st.subheader(f"🎬 JOB {jid}")

        if not job["download_done"]:
            st.progress(job["progress"])
            st.write("⬇️ Downloading...")
        else:
            st.success("Download selesai")
            if job["ffmpeg"] is None:
                threading.Thread(
                    target=ffmpeg_loop,
                    args=(job["path"], job["key"], job["shorts"], jid),
                    daemon=True
                ).start()
                st.info("📡 Streaming dimulai")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"STOP {jid}"):
                job["active"] = False
                if job["ffmpeg"]:
                    job["ffmpeg"].terminate()
                st.warning("Streaming dihentikan")

        with col2:
            if st.button(f"DELETE {jid}"):
                job["active"] = False
                if job["ffmpeg"]:
                    job["ffmpeg"].terminate()
                if os.path.exists(job["path"]):
                    os.remove(job["path"])
                del st.session_state.jobs[jid]
                st.error("Job dihapus")

        st.divider()
