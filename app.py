"""
Streamlit Chat Interface - Giao diện giống ChatGPT
"""
import streamlit as st
from pathlib import Path
import sys
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag import RAGPipeline
from src.llm import LLMManager


# Page config
st.set_page_config(
    page_title="LocalAI Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giống ChatGPT (Light theme)
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main background - White like ChatGPT */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Sidebar - Light gray */
    [data-testid="stSidebar"] {
        background-color: #f9f9f9;
        border-right: 1px solid #e5e5e5;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem;
    }
    
    /* Chat messages container */
    .stChatMessage {
        max-width: 768px;
        margin: 0 auto;
        padding: 24px 0;
        background-color: transparent;
    }
    
    [data-testid="stChatMessageContent"] {
        font-size: 16px;
        line-height: 1.75;
        color: #333333;
    }
    
    /* Chat input container with plus button */
    .stChatInput {
        max-width: 768px !important;
        margin: 0 auto !important;
    }
    
    .stChatInput > div {
        border-radius: 26px !important;
        border: 1px solid #d9d9d9 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
        background-color: #f4f4f4 !important;
    }
    
    .stChatInput input, .stChatInput textarea {
        font-size: 16px !important;
        background-color: transparent !important;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        border: 1px solid #d9d9d9;
        background-color: #ffffff;
        color: #333333;
        font-weight: 500;
        padding: 8px 16px;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #f5f5f5;
        border-color: #b3b3b3;
    }
    
    /* Primary button (green) */
    .stButton > button[kind="primary"] {
        background-color: #10a37f;
        color: white;
        border: none;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1a7f64;
    }
    
    /* Title styling */
    h1, h2, h3 {
        color: #333333 !important;
    }
    
    /* Radio buttons */
    .stRadio > div {
        flex-direction: row;
        gap: 8px;
    }
    
    .stRadio label {
        background-color: #ffffff !important;
        border: 1px solid #d9d9d9 !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        cursor: pointer;
    }
    
    .stRadio label:hover {
        background-color: #f5f5f5 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-size: 14px;
        color: #666666;
        background-color: #f9f9f9;
        border-radius: 8px;
    }
    
    /* Upload area */
    [data-testid="stFileUploader"] {
        border: 2px dashed #d9d9d9;
        border-radius: 12px;
        padding: 20px;
    }
    
    /* Welcome message */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 50vh;
        text-align: center;
    }
    
    .welcome-title {
        font-size: 32px;
        font-weight: 600;
        color: #333333;
        margin-bottom: 8px;
    }
    
    /* Sidebar section headers */
    .sidebar-header {
        font-size: 12px;
        font-weight: 600;
        color: #666666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 16px 0 8px 0;
    }
    
    /* Chat history item */
    .chat-item {
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        color: #333333;
        margin: 2px 0;
    }
    
    .chat-item:hover {
        background-color: #ececec;
    }
    
    /* Model info badge */
    .model-badge {
        display: inline-block;
        background-color: #e7f5ee;
        color: #10a37f;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #10a37f transparent transparent transparent;
    }
    
    /* Custom chat input container */
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 300px;
        right: 0;
        padding: 20px 40px 30px 40px;
        background: linear-gradient(transparent, white 20%);
    }
    
    .chat-input-box {
        max-width: 768px;
        margin: 0 auto;
        background-color: #f4f4f4;
        border-radius: 26px;
        border: 1px solid #e0e0e0;
        padding: 8px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .plus-button {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 1px solid #d9d9d9;
        background-color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 18px;
        color: #666;
        transition: all 0.2s;
    }
    
    .plus-button:hover {
        background-color: #f0f0f0;
        border-color: #999;
    }
    
    /* File chip */
    .file-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #e7f5ee;
        color: #10a37f;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 13px;
        margin: 4px;
    }
    
    .file-chip-remove {
        cursor: pointer;
        font-weight: bold;
        margin-left: 4px;
    }
    
    /* File upload area */
    .upload-area {
        border: 2px dashed #10a37f;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        background-color: #f8fffe;
        margin-bottom: 16px;
    }
    
    .upload-area.dragover {
        background-color: #e7f5ee;
        border-color: #0d8a6a;
    }
    
    /* Hide default file uploader styling */
    .stFileUploader > div > div {
        padding: 0 !important;
    }
    
    .stFileUploader label {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_rag():
    """Initialize RAG pipeline (cached)"""
    return RAGPipeline()


@st.cache_resource
def init_llm():
    """Initialize LLM for direct chat (cached)"""
    return LLMManager()


def main():
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    
    if "show_upload" not in st.session_state:
        st.session_state.show_upload = False

    # Sidebar
    with st.sidebar:
        # Logo and title
        st.markdown("### 🤖 LocalAI Chat")
        
        # New chat button
        if st.button("➕  New chat", use_container_width=True, type="primary"):
            if st.session_state.messages:
                first_msg = st.session_state.messages[0]["content"][:35] + "..."
                st.session_state.chat_history.insert(0, {
                    "title": first_msg,
                    "messages": st.session_state.messages.copy()
                })
            st.session_state.messages = []
            st.session_state.chat_started = False
            st.rerun()
        
        st.markdown("---")
        
        # Mode selection
        mode = st.radio(
            "Chế độ",
            ["💬 Chat", "📚 RAG"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # RAG document upload
        if "RAG" in mode:
            st.markdown("")
            with st.expander("📁 Upload tài liệu"):
                uploaded_files = st.file_uploader(
                    "Kéo thả files vào đây",
                    type=["pdf", "txt", "docx"],
                    accept_multiple_files=True,
                    label_visibility="collapsed"
                )
                
                if uploaded_files:
                    if st.button("📤 Tải lên", use_container_width=True):
                        with st.spinner("Đang xử lý..."):
                            upload_dir = Path("data/raw")
                            upload_dir.mkdir(parents=True, exist_ok=True)
                            
                            for file in uploaded_files:
                                file_path = upload_dir / file.name
                                with open(file_path, "wb") as f:
                                    f.write(file.getbuffer())
                            
                            rag = init_rag()
                            count = rag.load_documents(str(upload_dir))
                            st.success(f"✅ Đã tải {count} chunks!")
            
            # Stats
            try:
                rag = init_rag()
                stats = rag.get_stats()
                st.markdown(f"""
                <span class="model-badge">📄 {stats['vector_store']['count']} documents</span>
                """, unsafe_allow_html=True)
            except:
                pass
        
        # Chat history
        if st.session_state.chat_history:
            st.markdown("---")
            st.markdown('<p class="sidebar-header">Lịch sử chat</p>', unsafe_allow_html=True)
            
            for i, chat in enumerate(st.session_state.chat_history[:8]):
                if st.button(f"💬 {chat['title']}", key=f"hist_{i}", use_container_width=True):
                    st.session_state.messages = chat["messages"].copy()
                    st.session_state.chat_started = True
                    st.rerun()
        
        # Footer
        st.markdown("---")
        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown("👤")
        with col2:
            st.markdown("**Local User**")
            st.caption("Qwen 2.5 • Nomic Embed")

    # Main content area
    if not st.session_state.chat_started and not st.session_state.messages:
        # Welcome screen
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="welcome-container">
                <div class="welcome-title">Tôi có thể giúp gì cho bạn?</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Display chat messages
        for message in st.session_state.messages:
            avatar = "👤" if message["role"] == "user" else "🤖"
            with st.chat_message(message["role"], avatar=avatar):
                # Show attached files if any
                if message.get("files"):
                    for fname in message["files"]:
                        st.markdown(f'<span class="file-chip">📎 {fname}</span>', unsafe_allow_html=True)
                
                st.markdown(message["content"])
                
                if message.get("sources"):
                    with st.expander("📚 Nguồn tham khảo"):
                        for i, source in enumerate(message["sources"], 1):
                            st.caption(f"**Nguồn {i}:** {source['content'][:150]}...")

    # Custom chat input with file upload - Plus button integrated
    
    # Show file upload popup when toggled
    if st.session_state.show_upload:
        st.markdown("""
        <div class="upload-area">
            <p style="margin: 0; color: #10a37f; font-size: 16px;">📁 Kéo thả file vào đây hoặc click để chọn</p>
            <p style="margin: 8px 0 0 0; color: #888; font-size: 13px;">Hỗ trợ: PDF, TXT, DOCX</p>
        </div>
        """, unsafe_allow_html=True)
        
        chat_files = st.file_uploader(
            "Upload",
            type=["pdf", "txt", "docx"],
            accept_multiple_files=True,
            key="chat_uploader",
            label_visibility="collapsed"
        )
        
        if chat_files:
            # Show uploaded files as chips
            file_cols = st.columns(len(chat_files) if len(chat_files) <= 4 else 4)
            for i, f in enumerate(chat_files):
                with file_cols[i % 4]:
                    st.markdown(f'<span class="file-chip">📎 {f.name}</span>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ Xác nhận upload", use_container_width=True, type="primary"):
                    # Save files and load to RAG
                    upload_dir = Path("data/raw")
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    
                    file_names = []
                    for file in chat_files:
                        file_path = upload_dir / file.name
                        with open(file_path, "wb") as f:
                            f.write(file.getbuffer())
                        file_names.append(file.name)
                    
                    # Load to RAG
                    rag = init_rag()
                    count = rag.load_documents(str(upload_dir))
                    
                    st.session_state.uploaded_files = file_names
                    st.session_state.show_upload = False
                    st.success(f"✅ Đã tải {len(file_names)} file ({count} chunks)")
                    st.rerun()
            
            with col2:
                if st.button("❌ Hủy", use_container_width=True):
                    st.session_state.show_upload = False
                    st.rerun()
    
    # Show currently attached files
    if st.session_state.uploaded_files:
        st.markdown("**📎 Files đã đính kèm:**")
        for fname in st.session_state.uploaded_files:
            st.markdown(f'<span class="file-chip">📎 {fname}</span>', unsafe_allow_html=True)
    
    # Plus button - positioned next to chat input using CSS
    st.markdown("""
    <style>
    /* Position the button container at bottom left of input */
    .element-container:has(#plus-btn-anchor) {
        position: fixed !important;
        bottom: 17px !important;
        left: calc(50% - 370px) !important;
        z-index: 10000 !important;
        width: auto !important;
    }
    
    @media (max-width: 850px) {
        .element-container:has(#plus-btn-anchor) {
            left: 28px !important;
        }
    }
    
    /* Style the button */
    .element-container:has(#plus-btn-anchor) button {
        width: 42px !important;
        height: 42px !important;
        min-width: 42px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        border: 1px solid #e0e0e0 !important;
        background-color: #fff !important;
        font-size: 20px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
    }
    
    .element-container:has(#plus-btn-anchor) button:hover {
        background-color: #f5f5f5 !important;
        border-color: #10a37f !important;
    }
    
    /* Chat input - add left padding for button */
    .stChatInput textarea,
    .stChatInput [data-baseweb="textarea"] textarea {
        padding-left: 56px !important;
    }
    </style>
    <span id="plus-btn-anchor"></span>
    """, unsafe_allow_html=True)
    
    if st.button("➕", key="plus_btn", help="Đính kèm file"):
        st.session_state.show_upload = not st.session_state.show_upload
        st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Nhập tin nhắn..."):
        st.session_state.chat_started = True
        
        # Include attached files in message
        attached_files = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else None
        
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "files": attached_files
        })
        
        with st.chat_message("user", avatar="👤"):
            if attached_files:
                for fname in attached_files:
                    st.markdown(f'<span class="file-chip">📎 {fname}</span>', unsafe_allow_html=True)
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            
            try:
                # Use RAG mode if files attached or RAG selected
                use_rag = "RAG" in mode or st.session_state.uploaded_files
                
                if use_rag:
                    rag = init_rag()
                    result = rag.query(prompt)
                    response = result["answer"]
                    sources = result.get("sources", [])
                else:
                    llm = init_llm()
                    response = llm.invoke(prompt)
                    sources = []
                
                # Typing effect
                displayed_text = ""
                for char in response:
                    displayed_text += char
                    message_placeholder.markdown(displayed_text + "▌")
                    time.sleep(0.008)
                message_placeholder.markdown(response)
                
                if sources:
                    with st.expander("📚 Nguồn tham khảo"):
                        for i, source in enumerate(sources, 1):
                            st.caption(f"**Nguồn {i}:** {source['content'][:150]}...")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "sources": sources if sources else None
                })
                
                # Clear attached files after sending
                st.session_state.uploaded_files = []
                    
            except Exception as e:
                error_msg = f"❌ Lỗi: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })


if __name__ == "__main__":
    main()
