"""
Streamlit Chat Interface - Giao diện giống ChatGPT
"""
import logging
import streamlit as st
from pathlib import Path
import sys
import time
import json

# Configure root logger so pipeline debug messages appear in the terminal.
# Change to logging.WARNING to silence them in production.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag import RAGPipeline
from src.security import (
    ACCESS_DENIED_MESSAGE,
    build_access_filter,
    check_question_permission,
    classify_question_category,
    normalize_department,
    normalize_role,
)
from src.storage import ChatStore


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
    header {visibility: visible;}
    
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
    """Initialize RAG pipeline (cached) and warm up the LLM in the background."""
    import threading
    rag = RAGPipeline()
    # Run warmup in a background thread so Streamlit is not blocked.
    # The first real query may still need to load the model, but the UI
    # will be responsive immediately.
    threading.Thread(target=rag.warmup, daemon=True, name="llm_warmup").start()
    return rag


@st.cache_resource
def init_chat_store():
    """Initialize persistent chat storage and apply retention policy."""
    return ChatStore()


def build_system_prompt_with_summary(summary: str) -> str:
    """Build response instruction with persistent rolling summary context."""
    base_prompt = (
        "Bạn là trợ lý học thuật chuyên phân tích tài liệu Quan hệ Quốc tế (QHQT). "
        "Hãy trả lời đúng trọng tâm câu hỏi, dựa trên ngữ cảnh truy xuất được từ tài liệu. "
        "Với câu hỏi tổng hợp hoặc phân tích, phải bao quát đầy đủ các ý chính có trong context, "
        "nhóm ý rõ ràng và giải thích quan hệ giữa các luận điểm thay vì chỉ liệt kê tên mục. "
        "Nếu context thiếu dữ liệu hoặc chưa đủ thông tin để kết luận một phần nào đó, hãy nói rõ giới hạn này. "
        "Luôn trả lời bằng tiếng Việt, mạch lạc, có phân tích, không bịa thêm ngoài tài liệu."
    )

    summary_text = (summary or "").strip()
    if not summary_text:
        return base_prompt

    return (
        f"{base_prompt}\n\n"
        "Tóm tắt hội thoại trước đó (để giữ mạch trao đổi):\n"
        f"{summary_text}\n\n"
        "Dùng tóm tắt này để hiểu ngữ cảnh câu hỏi hiện tại, "
        "nhưng thông tin factual phải bám tài liệu truy xuất."
    )


def format_user_memories(user_memories: list[dict]) -> str:
    """Format selected long-term user memories for prompt injection."""
    if not user_memories:
        return ""

    lines = []
    for mem in user_memories[:8]:
        mem_type = str(mem.get("memory_type", "fact")).strip().lower()
        content = str(mem.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"- ({mem_type}) {content}")

    return "\n".join(lines)


def build_system_prompt(summary: str, user_memories: list[dict]) -> str:
    """Build final system prompt from rolling summary and selected user memories."""
    prompt = build_system_prompt_with_summary(summary)
    memories_text = format_user_memories(user_memories)
    if not memories_text:
        return prompt

    return (
        f"{prompt}\n\n"
        "Bộ nhớ dài hạn của người dùng (chỉ dùng khi liên quan):\n"
        f"{memories_text}\n\n"
        "Các memory này là ngữ cảnh mềm: ưu tiên độ chính xác theo tài liệu truy xuất ở lượt hiện tại."
    )


def _source_file_name(metadata: dict) -> str:
    source = str(metadata.get("file_name") or metadata.get("source") or "Không rõ")
    return Path(source).name if source else "Không rõ"


def _source_location(metadata: dict) -> str:
    parts = []
    page_start = metadata.get("page_start")
    page_end = metadata.get("page_end")
    page = metadata.get("page_number") or metadata.get("page")
    chunk_index = metadata.get("chunk_index")
    section = metadata.get("section_title") or metadata.get("chapter_title")
    retrieval_method = metadata.get("retrieval_method")

    if page_start is not None and page_end is not None:
        if page_start == page_end:
            parts.append(f"trang {page_start}")
        else:
            parts.append(f"trang {page_start}-{page_end}")
    elif page is not None:
        parts.append(f"trang {page}")
    if chunk_index is not None:
        parts.append(f"chunk {chunk_index}")
    if section:
        parts.append(str(section))
    if retrieval_method:
        parts.append(str(retrieval_method))
    return " | ".join(parts)


def render_sources(sources: list[dict]) -> None:
    """Render retrieved source snippets in a compact citation panel."""
    if not sources:
        return

    with st.expander(f"📚 Nguồn tham khảo ({len(sources)})"):
        for i, source in enumerate(sources, 1):
            metadata = source.get("metadata", {}) or {}
            breadcrumb = source.get("breadcrumb") or metadata.get("breadcrumb", "")
            source_name = _source_file_name(metadata)
            location = _source_location(metadata)
            preview = str(source.get("content", "")).strip()

            st.markdown(f"**[{i}] {source_name}**")
            if location:
                st.caption(location)
            if breadcrumb:
                st.caption(str(breadcrumb))
            if preview:
                st.caption(preview[:260] + ("..." if len(preview) > 260 else ""))


def update_rolling_summary(rag: RAGPipeline, old_summary: str, recent_messages: list[dict]) -> str:
    """Update conversation summary from latest turns."""
    clipped_history = recent_messages[-8:]
    history_lines = []
    for msg in clipped_history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = str(msg.get("content", "")).strip()
        if content:
            history_lines.append(f"{role}: {content}")

    history_text = "\n".join(history_lines) if history_lines else "(không có)"
    prev_summary = (old_summary or "").strip() or "(trống)"

    summarize_prompt = f"""Bạn là bộ máy tóm tắt hội thoại.
Hãy cập nhật rolling summary ngắn gọn bằng tiếng Việt, tối đa 8 gạch đầu dòng.
Giữ thông tin còn giá trị cho lượt hỏi tiếp theo: mục tiêu, thuật ngữ, quyết định, ràng buộc.
Không thêm thông tin không có trong hội thoại.

Summary cũ:
{prev_summary}

Các tin nhắn gần nhất:
{history_text}

Trả ra duy nhất phần summary mới, không thêm lời mở đầu."""

    try:
        new_summary = rag.llm_manager.invoke(summarize_prompt).strip()
        return new_summary if new_summary else (old_summary or "")
    except Exception:
        return old_summary or ""


def extract_selected_user_memories(rag: RAGPipeline, recent_messages: list[dict]) -> list[dict]:
    """Extract stable long-term user memories from recent dialogue."""
    clipped_history = recent_messages[-12:]
    history_lines = []
    for msg in clipped_history:
        role = "user" if msg.get("role") == "user" else "assistant"
        content = str(msg.get("content", "")).strip()
        if content:
            history_lines.append(f"{role}: {content}")

    if not history_lines:
        return []

    history_block = "\n".join(history_lines)

    memory_prompt = f"""Bạn là bộ trích xuất user memory dài hạn.
Từ hội thoại dưới đây, chỉ trích xuất các memory bền vững có ích cho các phiên sau.

Loại memory hợp lệ:
- preference: sở thích hoặc cách người dùng muốn được trả lời
- fact: thông tin bền vững về người dùng hoặc bối cảnh làm việc
- constraint: ràng buộc cố định người dùng yêu cầu

Quy tắc:
- Chỉ lấy memory rõ ràng, không suy diễn.
- Không lấy thông tin tạm thời theo 1 câu hỏi ngắn hạn.
- Trả về JSON array, mỗi phần tử có: memory_type, content, confidence (0..1).
- Tối đa 3 memory.
- Nếu không có memory phù hợp, trả về []

Hội thoại:
{history_block}

Trả về JSON duy nhất:"""

    try:
        raw = rag.llm_manager.invoke(memory_prompt).strip()
    except Exception:
        return []

    if not raw:
        return []

    cleaned = raw.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    json_text = cleaned[start : end + 1]
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    result = []
    for item in parsed[:5]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "memory_type": item.get("memory_type", ""),
                "content": item.get("content", ""),
                "confidence": item.get("confidence", 0.5),
            }
        )
    return result


def main():
    store = init_chat_store()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False

    if "auth_user_id" not in st.session_state:
        st.session_state.auth_user_id = None

    if "auth_user_email" not in st.session_state:
        st.session_state.auth_user_email = ""

    if "auth_user_role" not in st.session_state:
        st.session_state.auth_user_role = "Employee"

    if "auth_department" not in st.session_state:
        st.session_state.auth_department = "general"

    if "auth_department_id" not in st.session_state:
        st.session_state.auth_department_id = None

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "rolling_summary" not in st.session_state:
        st.session_state.rolling_summary = ""

    if "user_memories" not in st.session_state:
        st.session_state.user_memories = []

    # Sidebar
    with st.sidebar:
        # Logo and title
        st.markdown("### 🤖 LocalAI Chat")

        if not st.session_state.auth_user_id:
            auth_mode = st.radio(
                "Tài khoản",
                ["Đăng nhập", "Đăng ký"],
                horizontal=True,
            )

            if auth_mode == "Đăng nhập":
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Mật khẩu", type="password", key="login_password")
                if st.button("Đăng nhập", use_container_width=True, type="primary"):
                    user = store.authenticate_user(login_email, login_password)
                    if user:
                        st.session_state.auth_user_id = user["id"]
                        st.session_state.auth_user_email = user["email"]
                        st.session_state.auth_user_role = normalize_role(user.get("role"))
                        st.session_state.auth_department = normalize_department(user.get("department"))
                        st.session_state.auth_department_id = user.get("department_id")
                        st.session_state.messages = []
                        st.session_state.current_conversation_id = None
                        st.session_state.chat_started = False
                        st.session_state.rolling_summary = ""
                        st.session_state.user_memories = store.list_user_memories(user["id"], limit=12)
                        st.success("Đăng nhập thành công")
                        st.rerun()
                    else:
                        st.error("Sai email hoặc mật khẩu")
            else:
                register_email = st.text_input("Email đăng ký", key="register_email")
                register_password = st.text_input("Mật khẩu (>= 8 ký tự)", type="password", key="register_password")
                register_confirm = st.text_input("Nhập lại mật khẩu", type="password", key="register_confirm")
                if st.button("Tạo tài khoản", use_container_width=True, type="primary"):
                    if register_password != register_confirm:
                        st.error("Mật khẩu nhập lại không khớp")
                    else:
                        try:
                            user_id = store.register_user(register_email, register_password)
                            st.session_state.auth_user_id = user_id
                            st.session_state.auth_user_email = register_email.strip().lower()
                            st.session_state.auth_user_role = "Employee"
                            st.session_state.auth_department = "general"
                            st.session_state.auth_department_id = None
                            st.session_state.messages = []
                            st.session_state.current_conversation_id = None
                            st.session_state.chat_started = False
                            st.session_state.rolling_summary = ""
                            st.session_state.user_memories = store.list_user_memories(user_id, limit=12)
                            st.success("Tạo tài khoản thành công")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

            st.markdown("---")
            st.info("Đăng nhập để xem và lưu lịch sử chat theo từng tài khoản.")
        else:
            st.caption(f"Đăng nhập: {st.session_state.auth_user_email}")
            st.caption(
                f"Role: {st.session_state.auth_user_role} | Department: {st.session_state.auth_department}"
            )
            col_auth_1, col_auth_2 = st.columns(2)
            with col_auth_1:
                if st.button("➕ New chat", use_container_width=True, type="primary"):
                    st.session_state.messages = []
                    st.session_state.current_conversation_id = None
                    st.session_state.chat_started = False
                    st.session_state.rolling_summary = ""
                    st.rerun()
            with col_auth_2:
                if st.button("Đăng xuất", use_container_width=True):
                    store.log_audit(st.session_state.auth_user_id, "logout", "User logout")
                    st.session_state.auth_user_id = None
                    st.session_state.auth_user_email = ""
                    st.session_state.auth_user_role = "Employee"
                    st.session_state.auth_department = "general"
                    st.session_state.auth_department_id = None
                    st.session_state.current_conversation_id = None
                    st.session_state.messages = []
                    st.session_state.chat_started = False
                    st.session_state.rolling_summary = ""
                    st.session_state.user_memories = []
                    st.session_state.user_memories = []
                    st.rerun()

            st.markdown("---")
        
            st.markdown("---")

            # RAG document upload
            st.markdown("")
            with st.expander("📁 Upload tài liệu"):
                upload_allowed = st.session_state.auth_user_role in {"Admin", "Manager"}
                if not upload_allowed:
                    st.info("Chỉ Admin hoặc Manager được upload tài liệu.")
                    uploaded_files = []
                else:
                    department_options = ["general", "finance", "hr", "it", "legal", "security"]
                    if st.session_state.auth_user_role == "Manager":
                        department_options = sorted({"general", st.session_state.auth_department})
                    doc_department = st.selectbox(
                        "Department",
                        department_options,
                        index=0,
                    )
                    doc_sensitivity = st.selectbox(
                        "Sensitivity",
                        ["public", "internal", "confidential", "restricted"],
                        index=1,
                    )
                    allowed_role_options = ["Admin", "Manager", "Employee"]
                    default_allowed = ["Admin", "Manager"]
                    if doc_sensitivity in {"public", "internal"}:
                        default_allowed.append("Employee")
                    doc_allowed_roles = st.multiselect(
                        "Allowed roles",
                        allowed_role_options,
                        default=default_allowed,
                    )
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
                            if not doc_allowed_roles:
                                st.error("Phải chọn ít nhất một role được phép đọc tài liệu.")
                                st.stop()

                            for file in uploaded_files:
                                file_path = upload_dir / file.name
                                with open(file_path, "wb") as f:
                                    f.write(file.getbuffer())

                            upload_metadata = {
                                "department": doc_department,
                                "sensitivity": doc_sensitivity,
                                "allowed_roles": doc_allowed_roles,
                                "metadata_verified": True,
                                "uploaded_by": st.session_state.auth_user_id,
                            }
                            rag = init_rag()
                            count = 0
                            for file in uploaded_files:
                                file_path = upload_dir / file.name
                                count += rag.load_documents(
                                    str(file_path),
                                    is_directory=False,
                                    metadata=upload_metadata,
                                )
                            rag.clear_cache()
                            store.log_audit(
                                st.session_state.auth_user_id,
                                "document_upload",
                                {
                                    "file_count": len(uploaded_files),
                                    "chunks": count,
                                    "department": doc_department,
                                    "sensitivity": doc_sensitivity,
                                    "allowed_roles": doc_allowed_roles,
                                },
                            )
                            print(f"[INGESTION_DEBUG] Final result: {count} chunks loaded")
                            st.success(f"✅ Đã tải {count} chunks!")

            # Stats + Cache control
            try:
                rag = init_rag()
                stats = rag.get_stats()
                cache_hits = stats.get("cache_hits", 0)
                cache_misses = stats.get("cache_misses", 0)
                st.markdown(f"""
                <span class="model-badge">📄 {stats['vector_store']['count']} docs</span>
                """, unsafe_allow_html=True)
                st.caption(f"Cache: {cache_hits} hits / {cache_misses} misses")
                if st.button("🗑️ Clear Cache", use_container_width=True, help="Xóa cache khi vừa re-index tài liệu"):
                    rag.clear_cache()
                    st.success("✅ Cache đã được xóa")
            except Exception:
                pass

            # Chat history (tenant-isolated)
            st.markdown("---")
            st.markdown('<p class="sidebar-header">Lịch sử chat</p>', unsafe_allow_html=True)
            conversations = store.list_conversations(st.session_state.auth_user_id, limit=20)
            st.session_state.user_memories = store.list_user_memories(
                st.session_state.auth_user_id,
                limit=12,
            )
            if not conversations:
                st.caption("Chưa có cuộc chat nào")
            for conv in conversations:
                conv_title = conv["title"]
                if st.button(f"💬 {conv_title}", key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.current_conversation_id = conv["id"]
                    st.session_state.messages = store.get_messages(
                        st.session_state.auth_user_id,
                        conv["id"],
                    )
                    st.session_state.rolling_summary = store.get_conversation_summary(
                        st.session_state.auth_user_id,
                        conv["id"],
                    )
                    st.session_state.chat_started = bool(st.session_state.messages)
                    st.rerun()

            with st.expander("🧠 User memories", expanded=False):
                if not st.session_state.user_memories:
                    st.caption("Chưa có memory dài hạn")
                else:
                    for memory in st.session_state.user_memories[:8]:
                        mem_type = memory.get("memory_type", "fact")
                        conf = float(memory.get("confidence", 0.5))
                        content = memory.get("content", "")
                        st.caption(f"• ({mem_type}, {conf:.2f}) {content}")

            # Footer
            st.markdown("---")
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("👤")
            with col2:
                st.markdown("**Local User**")
                st.caption("Qwen 2.5 • Nomic Embed")

    # Main content area
    if not st.session_state.auth_user_id:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("Vui lòng đăng nhập hoặc đăng ký để bắt đầu chat và lưu lịch sử.")
        return

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
                    render_sources(message["sources"])

    # Chat input
    if prompt := st.chat_input("Nhập tin nhắn..."):
        st.session_state.chat_started = True
        question_category = classify_question_category(prompt)
        access_filter = build_access_filter(
            st.session_state.auth_user_role,
            st.session_state.auth_department,
        )
        question_allowed = check_question_permission(
            st.session_state.auth_user_role,
            st.session_state.auth_department,
            question_category,
        )

        if not st.session_state.current_conversation_id:
            conversation_title = (prompt.strip()[:50] + "...") if len(prompt.strip()) > 50 else prompt.strip()
            st.session_state.current_conversation_id = store.create_conversation(
                st.session_state.auth_user_id,
                conversation_title or "Chat mới",
            )
            st.session_state.rolling_summary = ""

        store.append_message(
            user_id=st.session_state.auth_user_id,
            conversation_id=st.session_state.current_conversation_id,
            role="user",
            content=prompt,
            sources=None,
        )
        
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt
        })
        
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            if not question_allowed:
                response = ACCESS_DENIED_MESSAGE
                message_placeholder.markdown(response)
                store.log_audit(
                    st.session_state.auth_user_id,
                    "question_denied",
                    {
                        "role": st.session_state.auth_user_role,
                        "department": st.session_state.auth_department,
                        "category": question_category,
                        "question_preview": prompt[:160],
                    },
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                })
                store.append_message(
                    user_id=st.session_state.auth_user_id,
                    conversation_id=st.session_state.current_conversation_id,
                    role="assistant",
                    content=response,
                    sources=None,
                )
                return
            
            try:
                rag = init_rag()
                system_prompt = build_system_prompt(
                    summary=st.session_state.rolling_summary,
                    user_memories=st.session_state.user_memories,
                )

                from src.config import STREAMING_ENABLED

                if STREAMING_ENABLED:
                    # ── True token streaming ──────────────────────────────
                    # Stream tokens directly from Ollama — no time.sleep() needed.
                    displayed_text = ""
                    sources: list = []
                    stream_result: dict = {}
                    message_placeholder.markdown("Đang tìm tài liệu và chuẩn bị câu trả lời...")
                    try:
                        for token in rag.query_stream(
                            prompt,
                            system_prompt=system_prompt,
                            chat_history=st.session_state.messages[:-1],
                            on_complete=stream_result.update,
                            access_filter=access_filter,
                        ):
                            displayed_text += token
                            message_placeholder.markdown(displayed_text + "▌")
                        message_placeholder.markdown(displayed_text)
                        response = displayed_text
                        sources = stream_result.get("sources", [])
                    except Exception as stream_exc:
                        # Streaming failed — fall back to non-streaming
                        st.warning(f"Streaming failed ({stream_exc}), retrying…")
                        result = rag.query(
                            prompt,
                            system_prompt=system_prompt,
                            chat_history=st.session_state.messages[:-1],
                            access_filter=access_filter,
                        )
                        response = result["answer"]
                        sources = result.get("sources", [])
                        message_placeholder.markdown(response)
                else:
                    # ── Non-streaming fallback ────────────────────────────
                    result = rag.query(
                        prompt,
                        system_prompt=system_prompt,
                        chat_history=st.session_state.messages[:-1],
                        access_filter=access_filter,
                    )
                    response = result["answer"]
                    sources = result.get("sources", [])
                    message_placeholder.markdown(response)
                
                if sources:
                    render_sources(sources)
                store.log_audit(
                    st.session_state.auth_user_id,
                    "question_allowed",
                    {
                        "role": st.session_state.auth_user_role,
                        "department": st.session_state.auth_department,
                        "category": question_category,
                        "question_preview": prompt[:160],
                        "retrieved_chunk_ids": [
                            str((source.get("metadata") or {}).get("chunk_id")
                                or (source.get("metadata") or {}).get("document_id")
                                or "")
                            for source in sources[:20]
                        ],
                    },
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "sources": sources if sources else None
                })
                store.append_message(
                    user_id=st.session_state.auth_user_id,
                    conversation_id=st.session_state.current_conversation_id,
                    role="assistant",
                    content=response,
                    sources=sources if sources else None,
                )

                # ── Async post-response tasks ─────────────────────────────
                # Submit rolling-summary update and memory extraction to run
                # in background threads so the UI is unblocked immediately.
                from src.config import ASYNC_POST_PROCESSING_ENABLED

                _messages_snapshot = list(st.session_state.messages)
                _conv_id = st.session_state.current_conversation_id
                _user_id = st.session_state.auth_user_id
                _old_summary = st.session_state.rolling_summary

                def _update_summary():
                    new_summary = update_rolling_summary(
                        rag=rag,
                        old_summary=_old_summary,
                        recent_messages=_messages_snapshot,
                    )
                    store.upsert_conversation_summary(
                        user_id=_user_id,
                        conversation_id=_conv_id,
                        summary=new_summary,
                        last_message_id=None,
                    )
                    # Update session state from background thread is not safe in
                    # Streamlit — the next rerun will re-fetch from DB instead.

                def _extract_memories():
                    extracted = extract_selected_user_memories(
                        rag=rag,
                        recent_messages=_messages_snapshot,
                    )
                    if extracted:
                        store.upsert_user_memories(
                            user_id=_user_id,
                            memories=extracted,
                            min_confidence=0.7,
                            max_memories=50,
                        )

                if ASYNC_POST_PROCESSING_ENABLED:
                    rag.post_task_executor.submit(
                        _update_summary, task_name="rolling_summary_update"
                    )
                    rag.post_task_executor.submit(
                        _extract_memories, task_name="memory_extraction"
                    )
                else:
                    # Synchronous fallback
                    _update_summary()
                    _extract_memories()
                    st.session_state.user_memories = store.list_user_memories(
                        _user_id, limit=12
                    )
                    
            except Exception as e:
                error_msg = f"❌ Lỗi: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                store.append_message(
                    user_id=st.session_state.auth_user_id,
                    conversation_id=st.session_state.current_conversation_id,
                    role="assistant",
                    content=error_msg,
                    sources=None,
                )


if __name__ == "__main__":
    main()
