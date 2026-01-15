import sys
import subprocess
import threading
import os
import time
import streamlit as st
import tempfile
import shutil

# Install dependencies jika belum ada
def install_package(package):
    try:
        __import__(package.replace("-", ""))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install paket yang diperlukan
install_package("streamlit")
install_package("streamlit-option-menu")

from streamlit_option_menu import option_menu


def optimize_video_for_streaming(video_path, output_path, is_shorts=False):
    """Optimasi video untuk streaming dengan kompresi"""
    try:
        st.info("🔧 Mengoptimasi video untuk streaming...")
        
        scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"{scale_filter},fps=30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-crf", "23",  # Quality: lower = better quality, higher = smaller size
            "-b:v", "2000k",
            "-maxrate", "2500k",
            "-bufsize", "5000k",
            "-g", "60",
            "-keyint_min", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-movflags", "+faststart",
            "-y",  # Overwrite output file
            output_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode == 0:
            st.success(f"✅ Video berhasil dioptimasi! Ukuran: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
            return output_path
        else:
            st.error(f"❌ Error optimasi: {process.stderr}")
            return video_path
    except Exception as e:
        st.error(f"❌ Error optimasi video: {e}")
        return video_path


def run_ffmpeg_stream(video_path, stream_key, is_shorts, log_callback):
    """Menjalankan streaming ke YouTube"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    # Gunakan video asli untuk streaming
    scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"
    
    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-re",  # Real-time mode
        "-i", video_path,
        "-vf", f"{scale_filter},fps=30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "2500k",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-g", "60",
        "-keyint_min", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",
        output_url
    ]
    
    log_callback(f"🚀 Memulai streaming dengan command: {' '.join(cmd[:5])}...")
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                log_callback(line.strip())
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code:
            log_callback(f"⚠️ Proses streaming berhenti dengan kode: {return_code}")
        else:
            log_callback("✅ Streaming berhasil dihentikan")
            
    except Exception as e:
        log_callback(f"❌ Error streaming: {str(e)}")
    finally:
        log_callback("📴 Streaming selesai")


def main():
    st.set_page_config(
        page_title="YouTube Live Streamer Pro",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS styling
    st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #FF0000, #FF6B6B);
        color: white;
        font-weight: bold;
        border: none;
        padding: 12px;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background: linear-gradient(45deg, #CC0000, #FF5252);
    }
    .video-info {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .log-container {
        background: #1e1e1e;
        color: #00ff00;
        padding: 15px;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar menu
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1384/1384060.png", width=100)
        st.title("🎬 Streamer Pro")
        
        selected = option_menu(
            menu_title=None,
            options=["📤 Upload Video", "⚙️ Settings", "📊 Stats"],
            icons=["cloud-upload", "gear", "graph-up"],
            default_index=0,
        )
    
    # Main content
    st.title("🎥 YouTube Live Streamer Pro")
    st.markdown("---")
    
    # Tab untuk streaming
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Stream", "📁 File Manager", "📈 Logs"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Upload video dengan chunk untuk file besar
            uploaded_file = st.file_uploader(
                "📁 Upload Video (MP4, MKV, AVI, MOV) - Max 2GB",
                type=['mp4', 'mkv', 'avi', 'mov', 'flv'],
                help="Upload video untuk di-streaming"
            )
            
            if uploaded_file:
                # Tampilkan info video
                file_size_mb = uploaded_file.size / (1024 * 1024)
                
                with st.expander("📊 Video Info", expanded=True):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("Ukuran File", f"{file_size_mb:.2f} MB")
                    with col_info2:
                        st.metric("Format", uploaded_file.type)
                    with col_info3:
                        st.metric("Status", "✅ Siap" if file_size_mb < 1000 else "⚠️ Perlu Optimasi")
                
                # Simpan file ke temporary directory
                temp_dir = tempfile.mkdtemp()
                video_path = os.path.join(temp_dir, uploaded_file.name)
                
                with st.spinner(f"⏳ Menyimpan file ({file_size_mb:.1f} MB)..."):
                    with open(video_path, "wb") as f:
                        # Baca dalam chunk untuk file besar
                        chunk_size = 1024 * 1024 * 10  # 10MB chunks
                        progress_bar = st.progress(0)
                        
                        for i, chunk in enumerate(uploaded_file.getbuffer()):
                            f.write(chunk)
                            if (i + 1) % (chunk_size // len(chunk)) == 0:
                                progress = min((i + 1) / (file_size_mb * 1024), 1.0)
                                progress_bar.progress(progress)
                        
                        progress_bar.progress(1.0)
                        st.session_state['video_path'] = video_path
                        st.session_state['temp_dir'] = temp_dir
                        st.success(f"✅ Video '{uploaded_file.name}' berhasil diupload!")
            
            # Input stream key
            st.subheader("🔐 YouTube Stream Key")
            stream_key = st.text_input(
                "Masukkan Stream Key Anda:",
                type="password",
                help="Dapatkan dari YouTube Studio > Live Streaming"
            )
            
            # Settings
            st.subheader("⚙️ Streaming Settings")
            col_set1, col_set2 = st.columns(2)
            with col_set1:
                is_shorts = st.checkbox("📱 Mode Shorts (9:16)", value=False)
                auto_optimize = st.checkbox("🔧 Auto Optimize", value=True)
            with col_set2:
                stream_quality = st.selectbox(
                    "Quality",
                    ["HD (720p)", "Full HD (1080p)", "Custom"],
                    index=0
                )
        
        with col2:
            st.subheader("🎯 Quick Actions")
            
            if 'video_path' in st.session_state and stream_key:
                if st.button("🚀 Start Streaming", type="primary", use_container_width=True):
                    with st.spinner("🔄 Memulai streaming..."):
                        # Optimasi video jika diperlukan
                        if auto_optimize and file_size_mb > 500:
                            optimized_path = os.path.join(st.session_state['temp_dir'], "optimized.mp4")
                            st.session_state['video_path'] = optimize_video_for_streaming(
                                st.session_state['video_path'],
                                optimized_path,
                                is_shorts
                            )
                        
                        # Jalankan streaming di thread terpisah
                        st.session_state['streaming'] = True
                        st.session_state['logs'] = []
                        
                        def log_callback(msg):
                            if 'logs' in st.session_state:
                                st.session_state['logs'].append(f"{time.strftime('%H:%M:%S')} - {msg}")
                        
                        thread = threading.Thread(
                            target=run_ffmpeg_stream,
                            args=(st.session_state['video_path'], stream_key, is_shorts, log_callback),
                            daemon=True
                        )
                        st.session_state['stream_thread'] = thread
                        thread.start()
                        
                        st.success("✅ Streaming dimulai!")
                        st.balloons()
            
            if st.button("🛑 Stop Streaming", use_container_width=True):
                if 'streaming' in st.session_state and st.session_state['streaming']:
                    os.system("pkill -f ffmpeg")
                    st.session_state['streaming'] = False
                    st.warning("⏸️ Streaming dihentikan")
            
            if st.button("🧹 Clear All", use_container_width=True):
                keys = list(st.session_state.keys())
                for key in keys:
                    del st.session_state[key]
                st.rerun()
            
            st.markdown("---")
            st.subheader("📋 Tips")
            st.info("""
            1. Pastikan koneksi internet stabil
            2. Gunakan video H.264 untuk kompatibilitas terbaik
            3. Mode Shorts cocok untuk TikTok/YouTube Shorts
            4. File >500MB direkomendasikan di-optimasi
            """)
    
    with tab2:
        st.subheader("📂 Video Files")
        
        # List video files in current directory
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.flv')
        video_files = [f for f in os.listdir('.') if f.lower().endswith(video_extensions)]
        
        if video_files:
            for video in video_files:
                col_file1, col_file2, col_file3, col_file4 = st.columns([3, 1, 1, 1])
                with col_file1:
                    st.write(f"🎬 {video}")
                with col_file2:
                    size_mb = os.path.getsize(video) / (1024 * 1024)
                    st.write(f"{size_mb:.1f} MB")
                with col_file3:
                    if st.button("📤 Select", key=f"select_{video}"):
                        st.session_state['video_path'] = video
                        st.success(f"✅ {video} dipilih!")
                with col_file4:
                    if st.button("🗑️", key=f"del_{video}"):
                        try:
                            os.remove(video)
                            st.rerun()
                        except:
                            st.error(f"❌ Gagal menghapus {video}")
        else:
            st.info("📭 Tidak ada video di direktori ini")
    
    with tab3:
        st.subheader("📈 Streaming Logs")
        
        if 'logs' in st.session_state and st.session_state['logs']:
            log_container = st.container()
            with log_container:
                st.markdown('<div class="log-container">', unsafe_allow_html=True)
                for log in st.session_state['logs'][-50:]:  # Tampilkan 50 log terakhir
                    st.text(log)
                st.markdown('</div>', unsafe_allow_html=True)
            
            col_log1, col_log2 = st.columns(2)
            with col_log1:
                if st.button("🔄 Refresh Logs"):
                    st.rerun()
            with col_log2:
                if st.button("🗑️ Clear Logs"):
                    st.session_state['logs'] = []
                    st.rerun()
        else:
            st.info("📭 Tidak ada logs streaming")
    
    # Cleanup pada session end
    if 'temp_dir' in st.session_state and os.path.exists(st.session_state['temp_dir']):
        if not st.session_state.get('streaming', False):
            try:
                shutil.rmtree(st.session_state['temp_dir'])
            except:
                pass
    
    # Footer
    st.markdown("---")
    st.caption("© 2024 YouTube Live Streamer Pro | Gunakan dengan bijak")


if __name__ == '__main__':
    main()
