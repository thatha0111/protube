import sys
import subprocess
import threading
import os
import streamlit.components.v1 as components

# Install streamlit jika belum ada
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st


def run_ffmpeg(video_path, stream_key, is_shorts, log_callback):
    """Menjalankan proses ffmpeg untuk streaming ke YouTube tanpa jeda antar-loop"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",              # Loop tanpa henti
        "-fflags", "+genpts",             # Generate timestamp baru agar tidak jeda
        "-re",                            # Real-time mode
        "-i", video_path,                 # Input file
        "-vf", scale_filter,              # Scaling sesuai mode
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",           # Mengurangi buffering encoder
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-keyint_min", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",  # Hindari metadata delay
        "-use_wallclock_as_timestamps", "1",  # Sinkronisasi waktu antar loop
        output_url
    ]

    log_callback(f"Menjalankan: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_callback(line.strip())
        process.wait()
    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback("Streaming selesai atau dihentikan.")


def main():
    st.set_page_config(page_title="Streaming YouTube Live", page_icon="🎥", layout="wide")

    # ✅ Naikkan limit upload ke 1000 MB
    st.config.set_option("server.maxUploadSize", 1000)

    st.title("🎥 Live Streaming ke YouTube")

    # Bagian iklan sponsor (opsional)
    show_ads = st.checkbox("Tampilkan Iklan", value=True)
    if show_ads:
        st.subheader("Iklan Sponsor")
        components.html(
            """
            <div style="background:#f0f2f6;padding:20px;border-radius:10px;text-align:center">
                <script type='text/javascript' 
                        src='//pl26562103.profitableratecpm.com/28/f9/95/28f9954a1d5bbf4924abe123c76a68d2.js'>
                </script>
                <p style="color:#888">Iklan akan muncul di sini</p>
            </div>
            """,
            height=300
        )

    # List video yang tersedia di direktori saat ini
    video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv'))]

    st.write("🎞️ Pilih video yang akan di-stream:")
    selected_video = st.selectbox("Pilih video", video_files) if video_files else None

    uploaded_file = st.file_uploader(
        "Atau upload video baru (format: mp4/flv - codec H264/AAC)", 
        type=['mp4', 'flv']
    )

    if uploaded_file:
        # Simpan file upload
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.read())
        st.success("✅ Video berhasil diupload!")
        video_path = uploaded_file.name
    elif selected_video:
        video_path = selected_video
    else:
        video_path = None

    # Input stream key YouTube
    stream_key = st.text_input("🔑 Masukkan YouTube Stream Key", type="password")
    is_shorts = st.checkbox("Mode Shorts (720x1280)", value=False)

    log_placeholder = st.empty()
    logs = []
    streaming = st.session_state.get('streaming', False)

    def log_callback(msg):
        logs.append(msg)
        try:
            log_placeholder.text("\n".join(logs[-20:]))
        except:
            print(msg)

    if 'ffmpeg_thread' not in st.session_state:
        st.session_state['ffmpeg_thread'] = None

    # Tombol Jalankan Streaming
    if st.button("🚀 Jalankan Streaming"):
        if not video_path or not stream_key:
            st.error("❌ Video dan Stream Key harus diisi!")
        else:
            st.session_state['streaming'] = True
            st.session_state['ffmpeg_thread'] = threading.Thread(
                target=run_ffmpeg,
                args=(video_path, stream_key, is_shorts, log_callback),
                daemon=True
            )
            st.session_state['ffmpeg_thread'].start()
            st.success("✅ Streaming dimulai ke YouTube Live!")

    # Tombol Stop Streaming
    if st.button("🛑 Stop Streaming"):
        st.session_state['streaming'] = False
        os.system("pkill ffmpeg")
        if os.path.exists("temp_video.mp4"):
            os.remove("temp_video.mp4")
        st.warning("⚠️ Streaming dihentikan!")

    # Tampilkan log terbaru
    log_placeholder.text("\n".join(logs[-20:]))


if __name__ == '__main__':
    main()
