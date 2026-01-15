import streamlit as st
import subprocess
import threading
import uuid
import re
import requests
import os
import time

# ==================================================
# GLOBAL SHARED STATE (THREAD SAFE)
# ==================================================
GLOBAL_JOBS = {}

DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==================================================
# STREAMLIT CONFIG
# ==================================================
st.set_page_config(
    page_title="GDrive PRO → YouTube Live (STABLE)",
    page_icon="📡",
    layout="wide"
)

# ==================================================
# GOOGLE DRIVE DOWNLOAD (NO STREAMLIT HERE)
# ==================================================
def download_gdrive(file_id, output_path, job_id):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    headers = {}
    downloaded = 0

    if os.path.exists(output_path):
        downloaded = os.path.getsize(output_path)
        headers["Range"] = f"bytes={downloaded}-"

    r = session.get(URL, params={"id": file_id}, headers=headers, stream=True)

    token = None
    for k, v in r.cookies.items():
        if k.startswith("download_warning"):
            token = v

    if token:
        r = session.get(
            URL,
            params={"id": file_id, "confirm": token},
            headers=headers,
            stream=True
        )

    total = int(r.headers.get("Content-Length", 0)) + downloaded

    mode = "ab" if downloaded else "wb"
    with open(output_path, mode) as f:
        for chunk in r.iter_content(1024 * 256):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)

            GLOBAL_JOBS[job_id]["progress"] = downloaded / total

    GLOBAL_JOBS[job_id]["download_done"] = True

# ==================================================
# FFMPEG AUTO RECONNECT (NO STREAMLIT)
# ==================================================
def ffmpeg_loop(job_id):
    job = GLOBAL_JOBS[job_id]
    scale = "720:1280" if job["shorts"] else "1280:720"
    rtmp = f"rtmp://a.rtmp.youtube.com/live2/{job['key']}"

    while job["active"]:
        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", job["path"],
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
        job["ffmpeg"] = p
        p.wait()
        time.sleep(3)

# ==================================================
# UI
# ==================================================
st.title("📡 Google Drive → YouTube Live (PRO STABLE)")
st.caption("No session_state in thread • Anti crash • GB+ safe")
st.divider()

with st.form("add"):
    gdrive = st.text_input("Google Drive Video Link")
    key = st.text_input("YouTube Stream Key", type="password")
    mode = st.radio("Mode", ["Landscape", "Shorts"])
    submit = st.form_submit_button("ADD STREAM")

    if submit:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", gdrive)
        if not match:
            st.error("Link Google Drive tidak valid")
        else:
            jid = str(uuid.uuid4())[:8]
            path = os.path.join(DOWNLOAD_DIR, f"{jid}.mp4")

            GLOBAL_JOBS[jid] = {
                "file_id": match.group(1),
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
                args=(match.group(1), path, jid),
                daemon=True
            ).start()

            st.success(f"Job {jid} dibuat")

st.divider()

# ==================================================
# JOB LIST UI (READ ONLY)
# ==================================================
for jid, job in list(GLOBAL_JOBS.items()):
    st.subheader(f"🎬 JOB {jid}")

    if not job["download_done"]:
        st.progress(job["progress"])
        st.write("⬇️ Downloading...")
    else:
        st.success("Download selesai")
        if job["ffmpeg"] is None:
            threading.Thread(
                target=ffmpeg_loop,
                args=(jid,),
                daemon=True
            ).start()
            st.info("📡 Streaming dimulai")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"STOP {jid}"):
            job["active"] = False
            if job["ffmpeg"]:
                job["ffmpeg"].terminate()
            st.warning("Stopped")

    with col2:
        if st.button(f"DELETE {jid}"):
            job["active"] = False
            if job["ffmpeg"]:
                job["ffmpeg"].terminate()
            if os.path.exists(job["path"]):
                os.remove(job["path"])
            del GLOBAL_JOBS[jid]
            st.error("Deleted")

    st.divider()
