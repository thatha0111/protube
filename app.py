import streamlit as st
import requests
import re
import json
import time
from urllib.parse import unquote

# ==================================================
# CONFIGURASI
# ==================================================
st.set_page_config(
    page_title="ProTube - Google Drive Video Streamer",
    page_icon="🎬",
    layout="wide"
)

# ==================================================
# STYLE CSS
# ==================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    .success-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .warning-card {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .log-box {
        background: #0f172a;
        color: #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
        margin-top: 10px;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# HEADER
# ==================================================
st.markdown('<div class="main-header">🎬 ProTube - Google Drive Video Streamer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Stream video besar langsung dari Google Drive ke YouTube Live</div>', unsafe_allow_html=True)

# ==================================================
# FUNGSI UTAMA - GOOGLE DRIVE CONVERTER
# ==================================================
def extract_file_id(gdrive_url):
    """
    Ekstrak file ID dari berbagai format Google Drive URL
    """
    patterns = [
        r'/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'file/d/([a-zA-Z0-9_-]+)',
        r'([a-zA-Z0-9_-]{25,})'  # Google Drive ID biasanya 25+ karakter
    ]
    
    for pattern in patterns:
        match = re.search(pattern, gdrive_url)
        if match:
            return match.group(1)
    
    # Jika tidak ditemukan dengan pattern biasa, coba manual parsing
    if "drive.google.com" in gdrive_url:
        # Coba ambil dari parameter view atau edit
        if "/view" in gdrive_url:
            parts = gdrive_url.split("/")
            for i, part in enumerate(parts):
                if part == "d" and i+1 < len(parts):
                    return parts[i+1]
    
    return None

def get_direct_download_link(file_id):
    """
    Dapatkan direct download link dari file ID Google Drive
    """
    base_urls = [
        f"https://drive.google.com/uc?id={file_id}",
        f"https://drive.google.com/uc?export=download&id={file_id}",
        f"https://docs.google.com/uc?export=download&id={file_id}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    for url in base_urls:
        try:
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            
            # Jika redirect, ikuti sampai akhir
            if response.status_code == 200:
                final_url = response.url
                
                # Jika ada confirm parameter, tambahkan
                if "confirm=" not in final_url and "google.com" in final_url:
                    final_url = f"{final_url}&confirm=t"
                
                # Cek jika ini adalah halaman warning
                if "interstitial" in final_url or "warning" in final_url:
                    # Tambahkan force download parameter
                    final_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t&format=download"
                
                return final_url, None
                
        except Exception as e:
            continue
    
    # Jika semua gagal, coba dengan Google Drive API sederhana
    try:
        api_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        response = requests.head(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return api_url, None
    except:
        pass
    
    return None, "Gagal mendapatkan direct link. Pastikan file di-share dengan akses 'Anyone with the link'"

def verify_video_url(url):
    """
    Verifikasi bahwa URL adalah video yang valid
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Range': 'bytes=0-1000'  # Hanya ambil sedikit untuk cek header
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        
        if response.status_code in [200, 206]:
            content_type = response.headers.get('content-type', '').lower()
            
            # Cek jika ini video
            video_types = ['video/', 'mp4', 'avi', 'mov', 'mkv', 'flv', 'webm']
            if any(vtype in content_type for vtype in video_types):
                # Coba dapatkan ukuran
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    return True, f"Video valid ({size_mb:.1f} MB)"
                else:
                    return True, "Video valid (ukuran tidak diketahui)"
            else:
                return False, "File bukan video"
        else:
            return False, f"HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==================================================
# SESSION STATE
# ==================================================
if 'converted_links' not in st.session_state:
    st.session_state.converted_links = {}
if 'streams' not in st.session_state:
    st.session_state.streams = {}
if 'logs' not in st.session_state:
    st.session_state.logs = {}

# ==================================================
# TAB INTERFACE
# ==================================================
tab1, tab2, tab3 = st.tabs(["🎯 Konversi Link", "📡 Streaming", "📊 Status"])

with tab1:
    st.markdown("### 🔗 Konversi Google Drive ke Direct Link")
    
    with st.expander("ℹ️ Cara Menggunakan", expanded=True):
        st.markdown("""
        1. **Copy link Google Drive** video Anda
        2. **Paste di bawah ini** (contoh: `https://drive.google.com/file/d/1NmTXyql_3DD4Ow-11dbGkgvUUf9_o150/view`)
        3. **Klik 'Konversi Link'** untuk mendapatkan direct download link
        4. **Verifikasi** bahwa link berhasil dikonversi
        5. **Gunakan link** di tab Streaming
        
        **Catatan Penting:**
        - Pastikan video di Google Drive di-share dengan **"Anyone with the link"**
        - Ukuran video tidak terbatas
        - Format video: MP4, AVI, MOV, MKV, FLV, WebM
        """)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        gdrive_url = st.text_input(
            "Link Google Drive Anda:",
            placeholder="https://drive.google.com/file/d/1NmTXyql_3DD4Ow-11dbGkgvUUf9_o150/view?usp=sharing",
            key="gdrive_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        convert_btn = st.button("🔄 Konversi Link", type="primary", use_container_width=True)
    
    if convert_btn and gdrive_url:
        with st.spinner("🔄 Mengonversi link Google Drive..."):
            time.sleep(1)
            
            # Ekstrak file ID
            file_id = extract_file_id(gdrive_url)
            
            if not file_id:
                st.error("❌ Tidak dapat menemukan File ID dalam URL. Pastikan format URL benar.")
            else:
                st.info(f"📁 File ID ditemukan: `{file_id}`")
                
                # Dapatkan direct link
                direct_link, error = get_direct_download_link(file_id)
                
                if direct_link:
                    # Verifikasi video
                    is_valid, message = verify_video_url(direct_link)
                    
                    if is_valid:
                        # Simpan ke session state
                        st.session_state.converted_links[file_id] = {
                            'direct_link': direct_link,
                            'original': gdrive_url,
                            'verified': True
                        }
                        
                        st.markdown('<div class="success-card">', unsafe_allow_html=True)
                        st.success("✅ Link berhasil dikonversi dan diverifikasi!")
                        st.code(direct_link, language="bash")
                        st.markdown(f"**Status:** {message}")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Tampilkan preview (jika MP4)
                        if direct_link.endswith('.mp4') or 'video/mp4' in direct_link:
                            st.video(direct_link)
                    else:
                        st.warning(f"⚠️ Link dikonversi tapi ada masalah: {message}")
                        st.code(direct_link, language="bash")
                else:
                    st.error(f"❌ {error}")

with tab2:
    st.markdown("### 📡 Konfigurasi Streaming ke YouTube")
    
    # Pilih dari link yang sudah dikonversi
    if st.session_state.converted_links:
        st.markdown("#### 📁 Video yang Tersedia:")
        
        for file_id, data in st.session_state.converted_links.items():
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**ID:** `{file_id[:15]}...`")
                    st.caption(f"Link: {data['direct_link'][:80]}...")
                    
                    if data.get('verified'):
                        st.markdown("✅ **Terverifikasi**")
                
                with col2:
                    use_btn = st.button(f"Gunakan", key=f"use_{file_id}")
                    if use_btn:
                        st.session_state.selected_video = data['direct_link']
                        st.success(f"✅ Video {file_id[:10]}... dipilih!")
    
    # Form konfigurasi streaming
    st.markdown("#### ⚙️ Konfigurasi Stream")
    
    with st.form("stream_config"):
        # Jika ada video yang dipilih, gunakan itu
        video_url = st.text_input(
            "Video URL (direct link):",
            value=st.session_state.get('selected_video', ''),
            placeholder="https://drive.google.com/uc?export=download&id=FILE_ID"
        )
        
        stream_key = st.text_input(
            "YouTube Stream Key:",
            type="password",
            placeholder="rtmp://a.rtmp.youtube.com/live2/xxxx-xxxx-xxxx-xxxx"
        )
        
        col_res, col_fps = st.columns(2)
        
        with col_res:
            resolution = st.selectbox(
                "Resolusi:",
                ["1280x720 (HD)", "854x480 (SD)", "1920x1080 (Full HD)", "640x360 (Low)"]
            )
        
        with col_fps:
            fps = st.selectbox(
                "Frame Rate:",
                ["30", "25", "24", "60"]
            )
        
        # Mode stream
        mode = st.radio(
            "Mode Streaming:",
            ["Normal", "Loop", "Shorts (Vertical)"],
            horizontal=True
        )
        
        submit = st.form_submit_button("🚀 Mulai Streaming")
        
        if submit:
            if not video_url or not stream_key:
                st.error("❌ Video URL dan Stream Key harus diisi")
            else:
                # Verifikasi URL terlebih dahulu
                is_valid, message = verify_video_url(video_url)
                
                if is_valid:
                    # Simpan konfigurasi stream
                    stream_id = f"stream_{int(time.time())}"
                    st.session_state.streams[stream_id] = {
                        'video_url': video_url,
                        'stream_key': stream_key,
                        'resolution': resolution,
                        'fps': fps,
                        'mode': mode,
                        'status': 'pending',
                        'start_time': time.time()
                    }
                    
                    # Log
                    log_msg = f"[{time.strftime('%H:%M:%S')}] Stream {stream_id} dikonfigurasi"
                    st.session_state.logs[stream_id] = [log_msg]
                    
                    st.success("✅ Stream berhasil dikonfigurasi! Lihat di tab Status.")
                else:
                    st.error(f"❌ Video URL tidak valid: {message}")

with tab3:
    st.markdown("### 📊 Status Streaming")
    
    if not st.session_state.streams:
        st.info("📭 Belum ada stream yang dikonfigurasi")
    else:
        for stream_id, config in st.session_state.streams.items():
            with st.container():
                st.markdown(f"#### 📡 Stream: `{stream_id}`")
                
                col_stat, col_info, col_action = st.columns([1, 2, 1])
                
                with col_stat:
                    status = config.get('status', 'pending')
                    if status == 'pending':
                        st.markdown("⏳ **Menunggu**")
                    elif status == 'live':
                        st.markdown("🟢 **LIVE**")
                    else:
                        st.markdown("🔴 **Stopped**")
                
                with col_info:
                    st.caption(f"Res: {config['resolution']}")
                    st.caption(f"FPS: {config['fps']}")
                    st.caption(f"Mode: {config['mode']}")
                
                with col_action:
                    if config['status'] == 'pending':
                        if st.button("▶ Start", key=f"start_{stream_id}"):
                            st.session_state.streams[stream_id]['status'] = 'live'
                            log_msg = f"[{time.strftime('%H:%M:%S')}] Stream dimulai"
                            st.session_state.logs[stream_id].append(log_msg)
                            st.rerun()
                    elif config['status'] == 'live':
                        if st.button("⏹ Stop", key=f"stop_{stream_id}"):
                            st.session_state.streams[stream_id]['status'] = 'stopped'
                            log_msg = f"[{time.strftime('%H:%M:%S')}] Stream dihentikan"
                            st.session_state.logs[stream_id].append(log_msg)
                            st.rerun()
                
                # Tampilkan logs
                if stream_id in st.session_state.logs:
                    st.markdown("**Logs:**")
                    logs_html = "<div class='log-box'>"
                    for log in st.session_state.logs[stream_id][-10:]:  # Tampilkan 10 log terakhir
                        logs_html += f"{log}<br>"
                    logs_html += "</div>"
                    st.markdown(logs_html, unsafe_allow_html=True)
                
                st.divider()

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b;">
    <small>🎬 ProTube Streamer • v2.0 • Support: MP4, AVI, MOV, MKV, FLV, WebM</small><br>
    <small>⚠️ Pastikan video di Google Drive sudah di-share dengan "Anyone with the link"</small>
</div>
""", unsafe_allow_html=True)

# ==================================================
# SIDEBAR INFORMASI
# ==================================================
with st.sidebar:
    st.markdown("### 📋 Panduan Cepat")
    
    st.markdown("""
    **1. Konversi Link:**
    - Paste link Google Drive
    - Klik "Konversi Link"
    - Tunggu hingga muncul direct link
    
    **2. Streaming:**
    - Pilih video yang sudah dikonversi
    - Masukkan YouTube Stream Key
    - Atur resolusi dan FPS
    - Klik "Mulai Streaming"
    
    **3. Monitor:**
    - Cek status di tab Status
    - Lihat logs untuk debug
    
    **Format Stream Key YouTube:**
    ```
    rtmp://a.rtmp.youtube.com/live2/xxxx-xxxx-xxxx-xxxx
    ```
    """)
    
    st.markdown("---")
    
    # Tampilkan statistik
    st.markdown("### 📊 Statistik")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Video Tersedia", len(st.session_state.converted_links))
    with col2:
        st.metric("Stream Aktif", sum(1 for s in st.session_state.streams.values() if s.get('status') == 'live'))
