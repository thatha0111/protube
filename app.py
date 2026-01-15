import sys
import subprocess
import threading
import os
import time
import streamlit as st
import tempfile
import shutil
from pathlib import Path

# Remove the automatic package installation section
# Streamlit Cloud doesn't allow installing packages at runtime

# Remove the import of streamlit-option-menu since it's not available in requirements.txt
# We'll use Streamlit's native components instead


def get_video_info(video_path):
    """Get video information using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,bit_rate,codec_name',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info = result.stdout.strip().split('\n')
            if len(info) >= 5:
                return {
                    'width': info[0],
                    'height': info[1],
                    'duration': float(info[2]) if info[2] != 'N/A' else 0,
                    'bitrate': info[3] if info[3] != 'N/A' else 'N/A',
                    'codec': info[4]
                }
    except:
        pass
    return None


def compress_video(input_path, output_path, target_size_mb=50):
    """Compress video to target size"""
    try:
        st.info(f"📦 Mengompresi video ke {target_size_mb}MB...")
        
        # Get video duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.returncode == 0 else 60
        
        # Calculate target bitrate (in kbps)
        target_size_bits = target_size_mb * 8 * 1024  # Convert MB to kilobits
        target_bitrate = int(target_size_bits / duration)  # kbps
        
        # Adjust bitrate for quality
        video_bitrate = max(500, min(target_bitrate - 128, 4000))
        audio_bitrate = 128
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-b:v', f'{video_bitrate}k',
            '-maxrate', f'{video_bitrate + 500}k',
            '-bufsize', f'{video_bitrate * 2}k',
            '-c:a', 'aac',
            '-b:a', f'{audio_bitrate}k',
            '-y',
            output_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            final_size = os.path.getsize(output_path) / (1024 * 1024)
            st.success(f"✅ Kompresi selesai! Ukuran akhir: {final_size:.2f}MB")
            return True
        else:
            st.error("❌ Gagal mengompresi video")
            return False
            
    except Exception as e:
        st.error(f"❌ Error kompresi: {str(e)}")
        return False


def save_uploaded_file(uploaded_file, temp_dir):
    """Save uploaded file with chunk processing"""
    try:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with st.spinner(f"💾 Menyimpan {uploaded_file.name}..."):
            with open(file_path, "wb") as f:
                # Process in chunks for large files
                chunk_size = 1024 * 1024 * 5  # 5MB chunks
                total_chunks = uploaded_file.size / chunk_size
                progress_bar = st.progress(0)
                
                for i in range(0, uploaded_file.size, chunk_size):
                    chunk = uploaded_file.getvalue()[i:i + chunk_size]
                    f.write(chunk)
                    progress = (i + len(chunk)) / uploaded_file.size
                    progress_bar.progress(progress)
                
                progress_bar.progress(1.0)
        
        return file_path
    except Exception as e:
        st.error(f"❌ Error menyimpan file: {str(e)}")
        return None


def run_streaming(video_path, stream_key, is_shorts, quality):
    """Run FFmpeg streaming process"""
    try:
        output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        # Quality settings
        quality_settings = {
            "720p": {"scale": "1280:720", "bitrate": "2500k"},
            "1080p": {"scale": "1920:1080", "bitrate": "4000k"},
            "shorts": {"scale": "720:1280", "bitrate": "2500k"}
        }
        
        scale = quality_settings["shorts"]["scale"] if is_shorts else quality_settings[quality]["scale"]
        bitrate = quality_settings["shorts"]["bitrate"] if is_shorts else quality_settings[quality]["bitrate"]
        
        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", video_path,
            "-vf", f"{scale},fps=30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-b:v", bitrate,
            "-maxrate", bitrate,
            "-bufsize", f"{int(bitrate[:-1]) * 2}k",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            output_url
        ]
        
        st.session_state['stream_process'] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Start log reader thread
        def read_logs():
            while st.session_state.get('streaming', False):
                try:
                    line = st.session_state['stream_process'].stdout.readline()
                    if line:
                        timestamp = time.strftime("%H:%M:%S")
                        st.session_state.setdefault('logs', []).append(f"{timestamp} - {line.strip()}")
                except:
                    break
        
        log_thread = threading.Thread(target=read_logs, daemon=True)
        log_thread.start()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error memulai streaming: {str(e)}")
        return False


def main():
    # Page configuration
    st.set_page_config(
        page_title="YouTube Live Streamer",
        page_icon="🎥",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(45deg, #FF0000, #FF6B6B);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .video-card {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stream-button {
        background: linear-gradient(45deg, #FF0000, #FF6B6B) !important;
        color: white !important;
        border: none !important;
    }
    .log-container {
        background: #1e1e1e;
        color: #00ff00;
        padding: 15px;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header"><h1>🎥 YouTube Live Streamer</h1></div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'streaming' not in st.session_state:
        st.session_state.streaming = False
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Pengaturan")
        
        # Stream key input
        stream_key = st.text_input(
            "🔑 YouTube Stream Key",
            type="password",
            help="Dapatkan dari YouTube Studio > Live Dashboard"
        )
        
        # Quality settings
        st.subheader("🎬 Kualitas Streaming")
        quality = st.selectbox(
            "Resolusi",
            ["720p", "1080p"],
            index=0
        )
        
        is_shorts = st.checkbox("📱 Mode Shorts (Vertikal)", value=False)
        
        # Compression settings
        st.subheader("📦 Kompresi Video")
        auto_compress = st.checkbox("Otomatis kompres video besar", value=True)
        compress_size = st.slider(
            "Target ukuran (MB)",
            min_value=10,
            max_value=200,
            value=50,
            help="Video akan dikompresi ke ukuran ini"
        )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File upload section
        st.subheader("📤 Upload Video")
        
        uploaded_file = st.file_uploader(
            "Pilih video untuk di-streaming",
            type=['mp4', 'avi', 'mov', 'mkv', 'flv'],
            help="Format yang didukung: MP4, AVI, MOV, MKV, FLV"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_size_mb = uploaded_file.size / (1024 * 1024)
            
            st.markdown(f"""
            <div class="video-card">
            <h4>📄 {uploaded_file.name}</h4>
            <p>📊 Ukuran: {file_size_mb:.2f} MB</p>
            <p>📝 Tipe: {uploaded_file.type}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Save to temp file
            temp_dir = tempfile.mkdtemp()
            temp_video_path = save_uploaded_file(uploaded_file, temp_dir)
            
            if temp_video_path:
                st.session_state.temp_dir = temp_dir
                st.session_state.video_path = temp_video_path
                
                # Show compression option for large files
                if file_size_mb > 100 and auto_compress:
                    if st.button("⚡ Kompres Video untuk Streaming", type="primary"):
                        compressed_path = os.path.join(temp_dir, "compressed.mp4")
                        if compress_video(temp_video_path, compressed_path, compress_size):
                            st.session_state.video_path = compressed_path
                            st.success("✅ Video siap untuk streaming!")
    
    with col2:
        # Streaming control
        st.subheader("🎮 Kontrol Streaming")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            start_disabled = not (stream_key and 'video_path' in st.session_state)
            if st.button(
                "🚀 Mulai Streaming",
                type="primary",
                disabled=start_disabled,
                use_container_width=True
            ):
                if not stream_key:
                    st.error("❌ Masukkan Stream Key terlebih dahulu")
                elif 'video_path' not in st.session_state:
                    st.error("❌ Upload video terlebih dahulu")
                else:
                    # Start streaming
                    if run_streaming(
                        st.session_state.video_path,
                        stream_key,
                        is_shorts,
                        quality
                    ):
                        st.session_state.streaming = True
                        st.success("✅ Streaming dimulai!")
                        st.balloons()
                    else:
                        st.error("❌ Gagal memulai streaming")
        
        with col_btn2:
            if st.button(
                "🛑 Stop Streaming",
                type="secondary",
                disabled=not st.session_state.streaming,
                use_container_width=True
            ):
                if 'stream_process' in st.session_state:
                    st.session_state.stream_process.terminate()
                    st.session_state.streaming = False
                    st.warning("⏸️ Streaming dihentikan")
        
        # Status indicator
        st.subheader("📊 Status")
        if st.session_state.streaming:
            st.success("🔴 LIVE - Sedang streaming")
        else:
            st.info("⚪ OFFLINE - Tidak streaming")
    
    # Logs section
    st.subheader("📜 Log Streaming")
    
    # Create log container
    log_container = st.container()
    
    with log_container:
        st.markdown('<div class="log-container">', unsafe_allow_html=True)
        if st.session_state.logs:
            for log in st.session_state.logs[-20:]:  # Show last 20 logs
                st.text(log)
        else:
            st.text("Tidak ada log untuk ditampilkan...")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Log controls
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        if st.button("🗑️ Hapus Log"):
            st.session_state.logs = []
            st.rerun()
    with col_log2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Cleanup on stop
    if not st.session_state.streaming and 'temp_dir' in st.session_state:
        try:
            shutil.rmtree(st.session_state.temp_dir)
            del st.session_state.temp_dir
            if 'video_path' in st.session_state:
                del st.session_state.video_path
        except:
            pass
    
    # Footer
    st.markdown("---")
    st.caption("⚠️ Pastikan Anda memiliki izin untuk menyiarkan konten ini")
    st.caption("🎬 Streamer v1.0 - Untuk file hingga 2GB")


if __name__ == '__main__':
    main()
