"""
Streamlit Chat Interface - Premium Corporate RAG UI Redesign
"""
import logging
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import time
import json
import datetime
from datetime import timezone

# Configure root logger so pipeline debug messages appear in the terminal.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag import RAGPipeline
from src.admin_analytics import (
    build_activity_snapshot,
    build_donut_html,
    build_excel_bytes,
    build_pdf_bytes,
    build_resource_status,
    build_warning_banner,
    fetch_audit_logs_in_range,
    normalize_period,
)
from src.admin_rbac import render_rbac_admin_page
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
    page_title="Corporate AI • Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS (Slate & Emerald Palette, Glassmorphism, Google Fonts)
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Core Typography and Globals */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #f8fafc !important;
        color: #0f172a;
    }
    
    /* Hide Streamlit default branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
    /* Dark Premium Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
        color: #f8fafc !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #f8fafc !important;
    }
    
    /* Sidebar Navigation Radio menu styled like vertical tabs */
    div.row-widget.stRadio > div {
        flex-direction: column !important;
        gap: 6px !important;
    }
    div.row-widget.stRadio label {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        background-color: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    div.row-widget.stRadio label:hover {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #ffffff !important;
    }
    div.row-widget.stRadio label[data-checked="true"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Document Card Grid Styling */
    .doc-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 220px;
        margin-bottom: 12px;
    }
    .doc-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    .doc-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .doc-icon {
        font-size: 24px;
    }
    .doc-badge {
        font-size: 10px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-done {
        background-color: #e7f5ee;
        color: #10a37f;
    }
    .badge-pending {
        background-color: #fef3c7;
        color: #d97706;
    }
    .badge-failed {
        background-color: #fee2e2;
        color: #ef4444;
    }
    .doc-title {
        font-size: 15px;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 6px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .doc-meta {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 10px;
    }
    .doc-desc {
        font-size: 13px;
        color: #475569;
        line-height: 1.5;
        margin-bottom: 16px;
        height: 60px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }
    
    /* Welcome cards / prompt templates */
    .welcome-prompt-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.2s;
        height: 100%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        text-align: left;
    }
    .welcome-prompt-card:hover {
        border-color: #10a37f;
        background-color: rgba(16, 163, 127, 0.02);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .welcome-prompt-icon {
        font-size: 20px;
        margin-bottom: 8px;
    }
    .welcome-prompt-title {
        font-size: 14px;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .welcome-prompt-desc {
        font-size: 12px;
        color: #64748b;
    }
    
    /* Chat bubbles styling */
    [data-testid="stChatMessage"] {
        padding: 20px 24px !important;
        border-radius: 12px !important;
        margin-bottom: 16px !important;
        max-width: 850px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    /* User chat bubble */
    [data-testid="stChatMessage"][data-test-avatar="user"] {
        background-color: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Assistant chat bubble */
    [data-testid="stChatMessage"][data-test-avatar="assistant"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
    }
    
    /* Sources cards container */
    .citation-card-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid #e2e8f0;
    }
    .citation-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
        color: #334155;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }
    .citation-card:hover {
        background-color: #f1f5f9;
        border-color: #cbd5e1;
    }
    .citation-file-icon {
        color: #ef4444; /* PDF color icon */
        font-weight: bold;
    }
    .citation-page-badge {
        background-color: #e2e8f0;
        color: #475569;
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
    }
    
    /* Metric Card for Executive Summary */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .metric-card-title {
        font-size: 12px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .metric-card-value {
        font-size: 13px;
        font-weight: 500;
        color: #334155;
        line-height: 1.4;
    }
    
    /* Scrollable Text Box for Doc Preview */
    .doc-preview-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 24px;
        height: 68vh;
        overflow-y: auto;
        font-size: 14px;
        line-height: 1.7;
        color: #334155;
    }
    
    /* Streamlit expander header styling */
    .streamlit-expanderHeader {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #475569 !important;
    }
    
    /* Custom buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    
    /* Sidebar buttons styling (Fixes white-blocks/invisible-text) */
    section[data-testid="stSidebar"] div.stButton > button,
    section[data-testid="stSidebar"] button[data-testid^="stBaseButton"],
    section[data-testid="stSidebar"] button,
    [data-testid="stSidebar"] div.stButton > button,
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"],
    [data-testid="stSidebar"] button,
    .stSidebar div.stButton > button,
    .stSidebar button {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        text-align: left !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
        box-shadow: none !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] button[data-testid^="stBaseButton"]:hover,
    section[data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] div.stButton > button:hover,
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"]:hover,
    [data-testid="stSidebar"] button:hover,
    .stSidebar div.stButton > button:hover,
    .stSidebar button:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
        color: #ffffff !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Force children/span/p/div inside sidebar buttons to inherit button text colors and be transparent */
    section[data-testid="stSidebar"] div.stButton > button *,
    section[data-testid="stSidebar"] button *,
    [data-testid="stSidebar"] button * {
        color: inherit !important;
        background-color: transparent !important;
    }
    
    /* Style trash/delete buttons inside history list columns (column 2) */
    section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) div.stButton > button,
    section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button,
    [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button,
    .stSidebar [data-testid="column"]:nth-child(2) button {
        text-align: center !important;
        padding: 8px !important;
        background-color: transparent !important;
        border-color: transparent !important;
    }
    section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) div.stButton > button:hover,
    section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button:hover,
    [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button:hover,
    .stSidebar [data-testid="column"]:nth-child(2) button:hover {
        background-color: rgba(239, 68, 68, 0.18) !important;
        color: #ef4444 !important;
        border-color: rgba(239, 68, 68, 0.35) !important;
    }
    
    /* Primary buttons in sidebar (like New Chat, Bắt đầu tải lên) */
    section[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"],
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background-color: #10a37f !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        text-align: center !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"]:hover,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover,
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
        background-color: #0d8a6a !important;
        box-shadow: 0 4px 12px rgba(16, 163, 127, 0.25) !important;
    }

    /* Sidebar inputs widgets style override */
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox select,
    [data-testid="stSidebar"] .stMultiSelect div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] .stTextInput input:focus,
    [data-testid="stSidebar"] .stSelectbox select:focus {
        border-color: #10a37f !important;
    }

    /* Sidebar expander styling */
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.04) !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    [data-testid="stSidebar"] .streamlit-expanderContent {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
    }
    
    /* Chat input styling */
    .stChatInput {
        max-width: 850px !important;
    }
    .stChatInput > div {
        border-radius: 24px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Sidebar Headers */
    .sidebar-header {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 20px 0 8px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_rag():
    """Initialize RAG pipeline (cached) and warm up the LLM in the background."""
    import threading
    rag = RAGPipeline()
    threading.Thread(target=rag.warmup, daemon=True, name="llm_warmup").start()
    return rag


@st.cache_resource
def init_chat_store():
    """Initialize persistent chat storage."""
    return ChatStore()


class LazyStoreProxy:
    """Proxy to lazily initialize ChatStore only on first use.

    This avoids running DB schema migrations at Streamlit startup.
    """
    def __init__(self):
        self._real: ChatStore | None = None

    def _ensure(self):
        if self._real is None:
            self._real = init_chat_store()

    def __getattr__(self, item):
        self._ensure()
        return getattr(self._real, item)


def build_system_prompt_with_summary(summary: str) -> str:
    """Build response instruction with persistent rolling summary context."""
    base_prompt = (
        "Bạn là trợ lý ảo chuyên nghiệp hỗ trợ giải đáp chính sách nội bộ của Công ty TNHH An Phát Digital. "
        "Hãy trả lời đúng trọng tâm câu hỏi, dựa trên ngữ cảnh truy xuất được từ tài liệu. "
        "Với câu hỏi tổng hợp hoặc phân tích, phải bao quát đầy đủ các ý chính có trong context, "
        "nhóm ý rõ ràng và giải thích chi tiết các quy định, con số hoặc quy trình thay vì chỉ liệt kê tên mục. "
        "Nếu context có các header [GROUP: ...], phải trả lời lần lượt theo từng nhóm đó; "
        "nhóm nào thiếu dữ liệu thì nói rõ context chưa đủ, không tự ý suy diễn hoặc bổ sung thông tin ngoài context. "
        "Nếu context thiếu dữ liệu hoặc chưa đủ thông tin để kết luận một phần nào đó, hãy nói rõ giới hạn này. "
        "Luôn trả lời bằng tiếng Việt, mạch lạc, khách quan, có phân tích cụ thể, không bịa thêm ngoài tài liệu."
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
    """Render retrieved source snippets as small premium citation cards."""
    if not sources:
        return

    st.markdown('<div class="citation-card-container">', unsafe_allow_html=True)
    cards_html = []
    for i, source in enumerate(sources, 1):
        metadata = source.get("metadata", {}) or {}
        source_name = _source_file_name(metadata)
        page = metadata.get("page_number") or metadata.get("page_start") or metadata.get("page") or "N/A"
        section = metadata.get("section_title") or "Quy định"
        
        # Tooltip for preview content
        preview = str(source.get("content", "")).strip()[:180].replace('"', '&quot;').replace('\n', ' ')
        tooltip_text = f"{section} | {preview}..."
        
        cards_html.append(f"""
        <div class="citation-card" title="{tooltip_text}">
            <span class="citation-file-icon">📄</span>
            <span style="font-weight: 500;">{source_name}</span>
            <span class="citation-page-badge">trang {page}</span>
        </div>
        """)
    st.markdown("".join(cards_html) + '</div>', unsafe_allow_html=True)


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
    - Bắt buộc: Nội dung (content) PHẢI ĐƯỢC VIẾT HOÀN TOÀN BẰNG TIẾNG VIỆT. Tuyệt đối không dùng tiếng Anh, tiếng Trung hay bất kỳ ngôn ngữ nào khác.
    
    Hội thoại:
    {history_block}
    
    Trả về JSON duy nhất (chỉ tiếng Việt):"""

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
        content = item.get("content", "")
        if any("\u4e00" <= ch <= "\u9fff" for ch in content):
            continue
        result.append(
            {
                "memory_type": item.get("memory_type", ""),
                "content": content,
                "confidence": item.get("confidence", 0.5),
            }
        )
    return result


def generate_doc_summary(rag: RAGPipeline, doc_name: str, full_text: str) -> dict:
    """Generate a high-quality summary for a document using LLM."""
    prompt = f"""Bạn là chuyên gia phân tích chính sách doanh nghiệp.
    Hãy phân tích tài liệu "{doc_name}" dưới đây và tóm tắt thành cấu trúc JSON với các trường:
    - "efficiency": Tóm tắt các lợi ích về hiệu quả hoạt động/chi phí hoặc mục tiêu cốt lõi (tối đa 25 từ).
    - "risk": Các biện pháp phòng ngừa rủi ro/chế tài/tuân thủ chính (tối đa 25 từ).
    - "outlook": Triển vọng tương lai/định hướng phát triển/quy trình kế tiếp (tối đa 25 từ).
    - "takeaways": Danh sách gồm 3-4 gạch đầu dòng các quy định cốt lõi nhất.

    Nội dung tài liệu (trích đoạn):
    {full_text[:4500]}

    Trả ra duy nhất một đối tượng JSON hợp lệ (bằng tiếng Việt):"""
    
    try:
        res = rag.llm_manager.invoke(prompt).strip()
        res_cleaned = res.replace("```json", "").replace("```", "").strip()
        start = res_cleaned.find("{")
        end = res_cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(res_cleaned[start:end+1])
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        
    # Fallback default values
    return {
        "efficiency": "Quy chuẩn hóa định mức chi phí và cải tiến hiệu quả vận hành nội bộ.",
        "risk": "Ngăn chặn thất thoát ngân sách và vi phạm quy định thông qua kiểm toán.",
        "outlook": "Số hóa quy trình hoàn ứng và tích hợp phê duyệt tự động trên hệ thống.",
        "takeaways": [
            "Đảm bảo tuân thủ nghiêm ngặt các hạn mức chi tiêu đã ban hành.",
            "Yêu cầu phê duyệt ngoại lệ rõ ràng khi phát sinh trường hợp vượt định mức.",
            "Nộp đầy đủ bằng chứng, hóa đơn hợp lệ trong thời hạn quy định."
        ]
    }


def main():
    # Avoid heavy DB work at startup: use a lazy proxy so ChatStore is
    # created only when first accessed (e.g., on login or first chat action).
    store = LazyStoreProxy()
    rag = init_rag()

    # Initialize session state variables
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

    if "auth_session_version" not in st.session_state:
        st.session_state.auth_session_version = None

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "rolling_summary" not in st.session_state:
        st.session_state.rolling_summary = ""

    if "user_memories" not in st.session_state:
        st.session_state.user_memories = []

    if "navigation" not in st.session_state:
        st.session_state.navigation = "Chat"

    if "selected_document" not in st.session_state:
        st.session_state.selected_document = None

    if "active_prompt" not in st.session_state:
        st.session_state.active_prompt = None

    # ── AUTHENTICATION - Centered Layout if not logged in ───────────────────────
    if not st.session_state.auth_user_id:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="font-size: 54px;">🤖</span>
                <h2 style="font-size: 28px; font-weight: 700; color: #0f172a; margin: 12px 0 4px 0;">Corporate AI</h2>
                <p style="color: #64748b; font-size: 15px;">Hệ thống quản lý tri thức & Trợ lý quy chế thông minh</p>
            </div>
            """, unsafe_allow_html=True)
            
            auth_mode = st.radio(
                "Tài khoản",
                ["Đăng nhập", "Đăng ký"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
            
            if auth_mode == "Đăng nhập":
                login_email = st.text_input("Email", placeholder="yourname@anphat.com")
                login_password = st.text_input("Mật khẩu", type="password", placeholder="••••••••")
                if st.button("Đăng nhập", use_container_width=True, type="primary"):
                    user = store.authenticate_user(login_email, login_password)
                    if user:
                        security_state = store.get_user_security_state(user["id"])
                        st.session_state.auth_user_id = user["id"]
                        st.session_state.auth_user_email = user["email"]
                        st.session_state.auth_user_role = normalize_role(user.get("role"))
                        st.session_state.auth_department = normalize_department(user.get("department"))
                        st.session_state.auth_department_id = user.get("department_id")
                        st.session_state.auth_session_version = (security_state or {}).get("session_version", user.get("session_version", 1))
                        st.session_state.messages = []
                        st.session_state.current_conversation_id = None
                        st.session_state.chat_started = False
                        st.session_state.rolling_summary = ""
                        st.session_state.user_memories = store.list_user_memories(user["id"], limit=12)
                        st.session_state.navigation = "Chat"
                        st.success("Đăng nhập thành công!")
                        st.rerun()
                    else:
                        st.error("Email hoặc mật khẩu không chính xác.")
            else:
                register_email = st.text_input("Email đăng ký", placeholder="yourname@anphat.com")
                register_password = st.text_input("Mật khẩu (tối thiểu 8 ký tự)", type="password", placeholder="••••••••")
                register_confirm = st.text_input("Nhập lại mật khẩu", type="password", placeholder="••••••••")
                if st.button("Tạo tài khoản", use_container_width=True, type="primary"):
                    if register_password != register_confirm:
                        st.error("Mật khẩu nhập lại không trùng khớp.")
                    else:
                        try:
                            user_id = store.register_user(register_email, register_password)
                            st.session_state.auth_user_id = user_id
                            st.session_state.auth_user_email = register_email.strip().lower()
                            st.session_state.auth_user_role = "Employee"
                            st.session_state.auth_department = "general"
                            st.session_state.auth_department_id = None
                            st.session_state.auth_session_version = 1
                            st.session_state.messages = []
                            st.session_state.current_conversation_id = None
                            st.session_state.chat_started = False
                            st.session_state.rolling_summary = ""
                            st.session_state.user_memories = store.list_user_memories(user_id, limit=12)
                            st.session_state.navigation = "Chat"
                            st.success("Tạo tài khoản thành công!")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
        return

    # ── DARK PREMIUM SIDEBAR (User logged in) ──────────────────────────────────
    security_state = None
    try:
        security_state = store.get_user_security_state(st.session_state.auth_user_id)
    except Exception:
        security_state = None
    if security_state:
        if not security_state.get("is_active") or security_state.get("session_version") != st.session_state.auth_session_version:
            store.log_audit(st.session_state.auth_user_id, "session_invalidated", {"reason": "force_logout_or_disable"})
            st.session_state.auth_user_id = None
            st.session_state.auth_user_email = ""
            st.session_state.auth_user_role = "Employee"
            st.session_state.auth_department = "general"
            st.session_state.auth_department_id = None
            st.session_state.auth_session_version = None
            st.session_state.current_conversation_id = None
            st.session_state.messages = []
            st.session_state.chat_started = False
            st.session_state.rolling_summary = ""
            st.session_state.user_memories = []
            st.session_state.navigation = "Chat"
            st.rerun()

    with st.sidebar:
        # App Logo Title
        st.markdown("""
        <div style="padding: 10px 0 20px 0;">
            <div style="font-size: 20px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                <span>🤖</span> Corporate AI
            </div>
            <div style="font-size: 11px; color: #94a3b8;">Internal Knowledge System</div>
        </div>
        """, unsafe_allow_html=True)

        # New Chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.current_conversation_id = None
            st.session_state.chat_started = False
            st.session_state.rolling_summary = ""
            st.session_state.navigation = "Chat"
            st.rerun()
            
        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
        
        # Navigation vertical tabs (simulated via custom styled radio)
        nav_options = {
            "💬 Trợ lý hỏi đáp": "Chat",
            "📂 Thư viện tài liệu": "Library",
            "📄 Chi tiết tài liệu": "Document Details"
        }
        if st.session_state.auth_user_role == "Admin":
            nav_options["⚙️ Quản trị RBAC"] = "RBAC Admin"
        if st.session_state.auth_user_role in {"Admin", "Manager"}:
            nav_options["📊 Dashboard AI"] = "AI Dashboard"
            nav_options["📈 Báo cáo AI"] = "AI Report"
        if st.session_state.auth_user_role == "Admin":
            nav_options["🛡️ Nhật ký hệ thống"] = "Audit Log"
        
        current_index = 0
        if st.session_state.navigation in nav_options.values():
            current_index = list(nav_options.values()).index(st.session_state.navigation)
            
        selected_nav_label = st.radio(
            "Điều hướng",
            options=list(nav_options.keys()),
            index=current_index,
            label_visibility="collapsed"
        )
        st.session_state.navigation = nav_options[selected_nav_label]

        # Statistics Badge
        try:
            stats = rag.get_stats()
            doc_count = stats['vector_store']['count']
            st.markdown(f"""
            <div style="margin-top: 15px;">
                <span class="doc-badge badge-active">📄 Database: {doc_count} docs</span>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

        # Chat History List (Tenant-Isolated)
        st.markdown('<p class="sidebar-header">Lịch sử hội thoại</p>', unsafe_allow_html=True)
        conversations = store.list_conversations(st.session_state.auth_user_id, limit=8)
        
        if not conversations:
            st.caption("Chưa có hội thoại nào")
        else:
            for conv in conversations:
                conv_title = conv["title"]
                col_conv, col_del = st.columns([5, 1])
                with col_conv:
                    if st.button(f"💬 {conv_title[:24]}...", key=f"conv_{conv['id']}", use_container_width=True, help=conv_title):
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
                        st.session_state.navigation = "Chat"
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{conv['id']}", help="Xóa lịch sử này"):
                        store.delete_conversation(st.session_state.auth_user_id, conv["id"])
                        if st.session_state.current_conversation_id == conv["id"]:
                            st.session_state.current_conversation_id = None
                            st.session_state.messages = []
                            st.session_state.rolling_summary = ""
                            st.session_state.chat_started = False
                        st.rerun()

        # Document Upload panel (Expander in sidebar)
        st.markdown('<p class="sidebar-header">Tác vụ hệ thống</p>', unsafe_allow_html=True)
        with st.expander("📤 Tải lên tài liệu"):
            upload_allowed = st.session_state.auth_user_role in {"Admin", "Manager"}
            if not upload_allowed:
                st.info("Chỉ quản trị viên mới có thể thêm tài liệu.")
            else:
                dept_options = ["general", "finance", "hr", "it", "legal", "security"]
                if st.session_state.auth_user_role == "Manager":
                    dept_options = sorted({"general", st.session_state.auth_department})
                doc_dept = st.selectbox("Phòng ban", dept_options, index=0)
                doc_sens = st.selectbox("Độ nhạy cảm", ["public", "internal", "confidential", "restricted"], index=1)
                
                role_opts = ["Admin", "Manager", "Employee"]
                default_allowed = ["Admin", "Manager"]
                if doc_sens in {"public", "internal"}:
                    default_allowed.append("Employee")
                doc_roles = st.multiselect("Nhóm quyền", role_opts, default=default_allowed)
                
                uploaded_files = st.file_uploader(
                    "Chọn files",
                    type=["pdf", "txt", "docx"],
                    accept_multiple_files=True,
                    label_visibility="collapsed"
                )
                
                if uploaded_files and st.button("Bắt đầu tải lên", use_container_width=True, type="primary"):
                    with st.spinner("Đang trích xuất và lưu trữ..."):
                        upload_dir = Path("data/raw")
                        upload_dir.mkdir(parents=True, exist_ok=True)
                        if not doc_roles:
                            st.error("Phải chọn tối thiểu 1 vai trò được phép truy cập.")
                            st.stop()
                            
                        for file in uploaded_files:
                            file_path = upload_dir / file.name
                            with open(file_path, "wb") as f:
                                f.write(file.getbuffer())
                                
                        meta = {
                            "department": doc_dept,
                            "sensitivity": doc_sens,
                            "allowed_roles": doc_roles,
                            "metadata_verified": True,
                            "uploaded_by": st.session_state.auth_user_id,
                        }
                        
                        count = 0
                        for file in uploaded_files:
                            file_path = upload_dir / file.name
                            count += rag.load_documents(str(file_path), is_directory=False, metadata=meta)
                        
                        rag.clear_cache()
                        store.log_audit(
                            st.session_state.auth_user_id,
                            "document_upload",
                            {"files": [f.name for f in uploaded_files], "chunks": count}
                        )
                        st.success(f"Nạp dữ liệu thành công: {count} chunks!")
                        st.rerun()

        # Cache clear in sidebar
        if st.button("🗑️ Clear Query Cache", use_container_width=True):
            rag.clear_cache()
            st.success("Clear Cache thành công!")

        # Profile details card at bottom
        st.markdown("---")
        email_display = st.session_state.auth_user_email.split('@')[0]
        role_display = st.session_state.auth_user_role
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
            <span style="font-size: 24px;">👤</span>
            <div>
                <div style="font-size: 13px; font-weight: 600; color: #ffffff;">{email_display}</div>
                <div style="font-size: 11px; color: #64748b;">Role: {role_display}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
            st.session_state.navigation = "Chat"
            st.rerun()


    # ── TAB 1: CHAT ASSISTANT (Trợ lý hỏi đáp) ──────────────────────────────────
    if st.session_state.navigation == "Chat":
        st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">Assistant Chat</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">Tra cứu thông tin chính sách, hướng dẫn nghiệp vụ thông minh qua ngôn ngữ tự nhiên.</p>', unsafe_allow_html=True)
        st.markdown("---")

        # Welcome screen if conversation is empty
        if not st.session_state.chat_started and not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 40px 0 20px 0;">
                <h1 style="font-size: 32px; font-weight: 700; color: #0f172a;">Tôi có thể giúp gì cho bạn hôm nay?</h1>
                <p style="color: #64748b; font-size: 15px; max-width: 600px; margin: 8px auto 0 auto;">
                    Hệ thống tích hợp quy chế tài chính, quy định đi công tác, chính sách làm việc từ xa và bảo mật IT của An Phát Digital.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Quick prompt templates
            st.markdown("<h4 style='font-size: 15px; font-weight: 600; color: #334155; margin-bottom: 12px; text-align: center;'>GỢI Ý CÂU HỎI NHANH</h4>", unsafe_allow_html=True)
            col_p1, col_p2 = st.columns(2)
            prompts = [
                ("🏨 Hạn mức khách sạn", "Tôi đi công tác TP.HCM cấp Manager thì hạn mức phòng khách sạn tối đa được chi trả là bao nhiêu?", "travel_expense_policy.pdf"),
                ("✈️ Quy định khoang vé bay", "Nhân viên cấp bậc Manager đi chuyến bay nội địa dưới 4 tiếng thì được đi khoang hạng nào?", "travel_expense_policy.pdf"),
                ("🍽️ Định mức phụ cấp ăn", "Quy định về phụ cấp ăn uống hàng ngày khi đi công tác nội địa là bao nhiêu?", "travel_expense_policy.pdf"),
                ("⏰ Thời hạn nộp hồ sơ", "Sau chuyến công tác, thời hạn tối đa để tôi nộp hồ sơ hoàn ứng claim chi phí là bao nhiêu ngày làm việc?", "travel_expense_policy.pdf"),
            ]
            
            with col_p1:
                for icon, title, desc in [prompts[0], prompts[2]]:
                    if st.button(f"{icon}\n\n{title}", key=f"quick_{title}", use_container_width=True):
                        st.session_state.chat_started = True
                        st.session_state.active_prompt = title
                        st.rerun()
            with col_p2:
                for icon, title, desc in [prompts[1], prompts[3]]:
                    if st.button(f"{icon}\n\n{title}", key=f"quick_{title}", use_container_width=True):
                        st.session_state.chat_started = True
                        st.session_state.active_prompt = title
                        st.rerun()
        else:
            # Render chat dialog flow
            for message in st.session_state.messages:
                avatar = "👤" if message["role"] == "user" else "🤖"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])
                    if message.get("sources"):
                        render_sources(message["sources"])

        # Check for active prompt from template buttons
        prompt = None
        if st.session_state.active_prompt:
            prompt = st.session_state.active_prompt
            st.session_state.active_prompt = None
        else:
            prompt = st.chat_input("Hỏi tôi về chính sách đi công tác, bảo mật, làm việc từ xa...")

        if prompt:
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

            # Lazy init conversation ID
            if not st.session_state.current_conversation_id:
                conv_title = (prompt.strip()[:40] + "...") if len(prompt.strip()) > 40 else prompt.strip()
                st.session_state.current_conversation_id = store.create_conversation(
                    st.session_state.auth_user_id,
                    conv_title or "Chat mới",
                )
                st.session_state.rolling_summary = ""

            # Append user message
            store.append_message(
                user_id=st.session_state.auth_user_id,
                conversation_id=st.session_state.current_conversation_id,
                role="user",
                content=prompt,
                sources=None,
            )
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

        # Handle active response generation
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            user_msg = st.session_state.messages[-1]["content"]
            
            with st.chat_message("assistant", avatar="🤖"):
                message_placeholder = st.empty()
                
                # Check ACL permissions
                question_allowed = check_question_permission(
                    st.session_state.auth_user_role,
                    st.session_state.auth_department,
                    classify_question_category(user_msg),
                )
                
                if not question_allowed:
                    response = ACCESS_DENIED_MESSAGE
                    message_placeholder.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    store.append_message(
                        user_id=st.session_state.auth_user_id,
                        conversation_id=st.session_state.current_conversation_id,
                        role="assistant",
                        content=response,
                        sources=None,
                    )
                    return

                try:
                    # Prepare RAG query
                    system_prompt = build_system_prompt(
                        summary=st.session_state.rolling_summary,
                        user_memories=st.session_state.user_memories,
                    )
                    
                    access_filter = build_access_filter(
                        st.session_state.auth_user_role,
                        st.session_state.auth_department,
                    )
                    
                    displayed_text = ""
                    sources = []
                    stream_result = {}
                    message_placeholder.markdown("🔍 đang tra cứu tài liệu và lập bối cảnh...")
                    
                    # Stream response directly from Ollama
                    for token in rag.query_stream(
                        user_msg,
                        system_prompt=system_prompt,
                        chat_history=st.session_state.messages[:-1],
                        on_complete=stream_result.update,
                        access_filter=access_filter,
                        rolling_summary=st.session_state.get("rolling_summary"),
                    ):
                        displayed_text += token
                        message_placeholder.markdown(displayed_text + "▌")
                    
                    message_placeholder.markdown(displayed_text)
                    response = displayed_text
                    sources = stream_result.get("sources", [])
                    
                    if sources:
                        render_sources(sources)
                        
                    # Save assistant response
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources if sources else None
                    })
                    timing = stream_result.get("timing", {}) if isinstance(stream_result, dict) else {}
                    source_names = []
                    for source in sources:
                        metadata = source.get("metadata", {}) if isinstance(source, dict) else {}
                        source_name = metadata.get("file_name") or metadata.get("source") or metadata.get("name")
                        if source_name:
                            source_names.append(str(source_name))
                    store.append_message(
                        user_id=st.session_state.auth_user_id,
                        conversation_id=st.session_state.current_conversation_id,
                        role="assistant",
                        content=response,
                        sources=sources if sources else None,
                    )
                    
                    # Log audit trail
                    store.log_audit(
                        st.session_state.auth_user_id,
                        "question_allowed",
                        {
                            "category": classify_question_category(user_msg),
                            "department": st.session_state.auth_department,
                            "role": st.session_state.auth_user_role,
                            "question_text": user_msg[:500],
                            "question_preview": user_msg[:120],
                            "sources_count": len(sources),
                            "sources": source_names,
                            "latency_ms": timing.get("total_ms", 0.0),
                            "ttft_ms": timing.get("ttft_ms", 0.0),
                        }
                    )

                    # Trigger async post-response task updates (memory extraction + summary)
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
                        rag.post_task_executor.submit(_update_summary, task_name="summary_update")
                        rag.post_task_executor.submit(_extract_memories, task_name="memory_extraction")
                    else:
                        _update_summary()
                        _extract_memories()
                        st.session_state.user_memories = store.list_user_memories(_user_id, limit=12)
                        
                    st.rerun()

                except Exception as e:
                    error_msg = f"❌ Hệ thống bận hoặc xảy ra lỗi: {str(e)}"
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    store.append_message(
                        user_id=st.session_state.auth_user_id,
                        conversation_id=st.session_state.current_conversation_id,
                        role="assistant",
                        content=error_msg,
                        sources=None,
                    )


    # ── TAB 2: DOCUMENT LIBRARY (Thư viện tài liệu) ──────────────────────────────
    elif st.session_state.navigation == "Library":
        st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">Document Library</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">Kho lưu trữ văn bản chính sách và hướng dẫn quy trình của hệ thống.</p>', unsafe_allow_html=True)
        st.markdown("---")

        # Fetch documents
        docs = rag.vector_store_manager.list_documents()

        # Filter layouts side-by-side with document grid
        col_filters, col_grid = st.columns([1, 3])

        # Render Left Column Filters
        with col_filters:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h4 style="font-size: 14px; font-weight: 700; color: #1e293b; margin-top: 0; margin-bottom: 15px; letter-spacing: 0.5px;">BỘ LỌC TÌM KIẾM</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Department checkboxes
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>PHÒNG BAN</p>", unsafe_allow_html=True)
            depts = ["general", "finance", "hr", "it", "legal", "security"]
            dept_names = {
                "general": "General Policies",
                "finance": "Finance & Tax",
                "hr": "Human Resources",
                "it": "IT & Engineering",
                "legal": "Legal & Compliance",
                "security": "Cybersecurity"
            }
            selected_depts = []
            for d in depts:
                if st.checkbox(dept_names[d], value=True, key=f"lib_dept_{d}"):
                    selected_depts.append(d)

            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

            # Date Filter Dropdown
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>THỜI GIAN TẢI LÊN</p>", unsafe_allow_html=True)
            time_filter = st.selectbox(
                "Thời gian",
                ["Tất cả", "30 ngày qua", "6 tháng qua"],
                label_visibility="collapsed"
            )

            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

            # File Format Pills
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>ĐỊNH DẠNG FILE</p>", unsafe_allow_html=True)
            formats = st.multiselect(
                "Định dạng",
                ["PDF", "DOCX", "TXT"],
                default=["PDF", "DOCX", "TXT"],
                label_visibility="collapsed"
            )

            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

            # Storage space progress bar
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>DUNG LƯỢNG LƯU TRỮ</p>", unsafe_allow_html=True)
            space_gb = round(len(docs) * 0.15 + 8.4, 1)
            st.progress(space_gb / 20.0)
            st.caption(f"**{space_gb} GB** / 20.0 GB")

        # Render Right Column Grid
        with col_grid:
            col_search_t, col_search_i = st.columns([2, 1])
            with col_search_t:
                st.markdown(f"##### Danh sách tài liệu ({len(docs)} tổng cộng)")
            with col_search_i:
                search_query = st.text_input("🔍", placeholder="Tìm tên file...", label_visibility="collapsed")

            # Apply filters to list
            filtered_docs = []
            for doc in docs:
                file_name = doc["file_name"]
                meta = doc.get("metadata") or {}
                dept = meta.get("department", "general")
                ext = Path(file_name).suffix[1:].upper()
                if ext == "MD":
                    ext = "TXT"

                if dept not in selected_depts:
                    continue
                if ext not in formats:
                    continue
                if search_query and search_query.lower() not in file_name.lower():
                    continue

                if time_filter != "Tất cả":
                    delta = datetime.datetime.now(timezone.utc) - doc["created_at"]
                    if time_filter == "30 ngày qua" and delta.days > 30:
                        continue
                    if time_filter == "6 tháng qua" and delta.days > 180:
                        continue

                filtered_docs.append(doc)

            # Render Document Card Grid (3 columns)
            if not filtered_docs:
                st.info("Không có tài liệu nào khớp với điều kiện tìm kiếm.")
            else:
                cols_per_row = 3
                rows = [filtered_docs[i:i + cols_per_row] for i in range(0, len(filtered_docs), cols_per_row)]
                
                for row_idx, row_docs in enumerate(rows):
                    cols = st.columns(cols_per_row)
                    for col_idx, doc in enumerate(row_docs):
                        with cols[col_idx]:
                            file_name = doc["file_name"]
                            meta = doc.get("metadata") or {}
                            dept = meta.get("department", "general").upper()
                            emb_status = doc.get("embedding_status", "DONE").upper()
                            created_str = doc["created_at"].strftime("%b %d, %Y")
                            
                            badge_cls = "badge-done"
                            if emb_status == "PROCESSING":
                                badge_cls = "badge-pending"
                            elif emb_status == "FAILED":
                                badge_cls = "badge-failed"

                            st.markdown(f"""
                            <div class="doc-card">
                                <div>
                                    <div class="doc-card-header">
                                        <span class="doc-icon">📄</span>
                                        <span class="doc-badge {badge_cls}">{emb_status}</span>
                                    </div>
                                    <div class="doc-title" title="{file_name}">{file_name}</div>
                                    <div class="doc-meta">{dept} • {created_str}</div>
                                    <div class="doc-desc">
                                        Tài liệu chính sách thuộc lĩnh vực {dept.lower()}. Mức bảo mật: {meta.get("sensitivity", "internal")}.
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Renders actual Streamlit interactive buttons below the HTML card
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                if st.button("Xem tóm tắt", key=f"sum_{doc['id']}", use_container_width=True):
                                    st.session_state.selected_document = doc
                                    st.session_state.navigation = "Document Details"
                                    st.rerun()
                            with btn_col2:
                                if st.button("Mở đọc", key=f"open_{doc['id']}", use_container_width=True):
                                    st.session_state.selected_document = doc
                                    st.session_state.navigation = "Document Details"
                                    st.rerun()


    # ── TAB 3: DOCUMENT DETAILS & SUMMARY (Báo cáo tóm tắt song song) ────────────
    elif st.session_state.navigation == "Document Details":
        docs = rag.vector_store_manager.list_documents()
        if not docs:
            st.info("Chưa có tài liệu nào trong hệ thống.")
            return

        if st.session_state.selected_document:
            selected_doc_id = st.session_state.selected_document.get("id")
        else:
            selected_doc_id = None

        selected_doc_label = st.selectbox(
            "Chọn tài liệu",
            options=[doc["id"] for doc in docs],
            format_func=lambda doc_id: next((doc["file_name"] for doc in docs if doc["id"] == doc_id), doc_id),
            index=next((idx for idx, doc in enumerate(docs) if doc["id"] == selected_doc_id), 0),
            key="document_details_selector",
        )
        doc = next(doc for doc in docs if doc["id"] == selected_doc_label)
        st.session_state.selected_document = doc

        doc_id = doc["id"]
        doc_name = doc["file_name"]
        
        # Load document text chunks
        chunks = rag.vector_store_manager.get_document_chunks(doc_id)
        full_text = "\n\n".join([c["content"] for c in chunks])

        # Header bar
        col_back, col_title = st.columns([1, 8])
        with col_back:
            if st.button("◀ Thư viện", use_container_width=True):
                st.session_state.navigation = "Library"
                st.rerun()
        with col_title:
            st.markdown(f'<h3 style="font-weight: 700; font-size: 20px; color: #0f172a; margin-top: 2px;">{doc_name}</h3>', unsafe_allow_html=True)
        st.markdown("---")

        # Split pane layout (Left: Text preview, Right: Executive Summary + QA)
        col_preview, col_summary = st.columns([3, 2])

        with col_preview:
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>NỘI DUNG TÀI LIỆU</p>", unsafe_allow_html=True)
            formatted_text = full_text.replace('\n', '<br/>')
            st.markdown(f"""
            <div class="doc-preview-box">
                {formatted_text}
            </div>
            """, unsafe_allow_html=True)

        with col_summary:
            st.markdown("<p style='font-size: 12px; font-weight: 600; color: #64748b;'>TÓM TẮT CHỈ SỐ (EXECUTIVE SUMMARY)</p>", unsafe_allow_html=True)
            
            # Cache the summary in session state to prevent repeatedly invoking LLM
            summary_state_key = f"doc_summary_{doc_id}"
            if summary_state_key not in st.session_state:
                with st.spinner("Đang phân tích và sinh tóm tắt chỉ số..."):
                    st.session_state[summary_state_key] = generate_doc_summary(rag, doc_name, full_text)
            
            summary_data = st.session_state[summary_state_key]

            # Render Metric cards
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">📈 Lợi ích vận hành (Efficiency Gains)</div>
                <div class="metric-card-value">{summary_data.get("efficiency", "")}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-title">⚠️ Phòng ngừa rủi ro (Risk Mitigation)</div>
                <div class="metric-card-value">{summary_data.get("risk", "")}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-title">🔮 Triển vọng phát triển (Projected Outlook)</div>
                <div class="metric-card-value">{summary_data.get("outlook", "")}</div>
            </div>
            """, unsafe_allow_html=True)

            # Render key action items
            st.markdown("##### Quy tắc cốt lõi (Key Takeaways)")
            for item in summary_data.get("takeaways", []):
                st.markdown(f"- [x] {item}")

            st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

            # Document-specific QA input box
            st.markdown("##### 💬 Hỏi đáp nhanh về tài liệu này")
            st.caption("Các câu hỏi dưới đây chỉ tìm kiếm thông tin và giải đáp trên duy nhất tài liệu này.")
            doc_query = st.text_input("Đặt câu hỏi cho tài liệu này...", key=f"query_doc_{doc_id}", placeholder="Hỏi về hạn mức, quy trình...")
            
            if doc_query:
                with st.spinner("Đang tìm kiếm..."):
                    # Build metadata filter restricting search solely to this document
                    access_filter = build_access_filter(
                        st.session_state.auth_user_role,
                        st.session_state.auth_department,
                    )
                    access_filter["document_id"] = doc_id
                    
                    # Run RAG query
                    result = rag.query(
                        question=doc_query,
                        k=3,
                        access_filter=access_filter
                    )
                    
                    # Display response in clean card
                    st.markdown(f"""
                    <div style="background-color: #e0f2fe; border-left: 4px solid #0284c7; padding: 16px; border-radius: 8px; font-size: 13px; line-height: 1.6; color: #0369a1; margin-top: 10px;">
                        <strong>Trợ lý AI trả lời:</strong><br/>
                        {result['answer']}
                    </div>
                    """, unsafe_allow_html=True)

    # ── TAB 4: AI DASHBOARD ────────────────────────────────────────────────────
    elif st.session_state.navigation == "AI Dashboard":
        if st.session_state.auth_user_role not in {"Admin", "Manager"}:
            st.error("Bạn không có quyền truy cập trang này.")
            return

        st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">📊 Dashboard theo dõi hệ thống AI</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">KPI cards, biểu đồ truy vấn, cảnh báo realtime và trạng thái tài nguyên.</p>', unsafe_allow_html=True)
        st.markdown("---")
        st.components.v1.html("<meta http-equiv='refresh' content='15'>", height=0)

        period_label_map = {
            "Hôm nay": "today",
            "7 ngày": "7d",
            "30 ngày": "30d",
            "Tùy chỉnh": "custom",
        }
        period_choice = st.radio("Khoảng thời gian", list(period_label_map.keys()), horizontal=True)

        custom_start = None
        custom_end = None
        if period_choice == "Tùy chỉnh":
            col_start, col_end = st.columns(2)
            with col_start:
                custom_start = st.date_input(
                    "Từ ngày",
                    value=datetime.date.today() - datetime.timedelta(days=7),
                )
            with col_end:
                custom_end = st.date_input("Đến ngày", value=datetime.date.today())

        dept_labels = {
            "all": "Tất cả phòng ban",
            "general": "General",
            "finance": "Finance",
            "hr": "HR",
            "it": "IT",
            "legal": "Legal",
            "security": "Security",
        }

        if st.session_state.auth_user_role == "Manager":
            selected_department = st.session_state.auth_department
            st.info(f"Bộ lọc phòng ban đang cố định theo quyền Manager: {dept_labels.get(selected_department, selected_department)}")
        else:
            selected_department = st.selectbox(
                "Phòng ban",
                ["all", "general", "finance", "hr", "it", "legal", "security"],
                format_func=lambda value: dept_labels.get(value, value),
            )

        try:
            start_dt, end_dt, period_display = normalize_period(
                period_label_map[period_choice],
                custom_start=custom_start,
                custom_end=custom_end,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        try:
            question_logs = fetch_audit_logs_in_range(
                store,
                start=start_dt,
                end=end_dt,
                event_type="question_allowed",
            )
        except Exception as exc:
            st.error(f"Không thể đọc query log: {exc}")
            return

        try:
            indexed_documents = rag.get_stats().get("vector_store", {}).get("count", 0)
        except Exception:
            indexed_documents = 0

        try:
            runtime_status = rag.llm_manager.get_runtime_status()
        except Exception:
            runtime_status = {"queue_waiting": 0, "max_queue_size": 0, "active_calls": 0}

        snapshot = build_activity_snapshot(
            question_logs,
            selected_department=selected_department,
            indexed_documents=indexed_documents,
            include_user_breakdown=False,
        )
        seven_day_question_df = snapshot["question_df"]
        try:
            seven_day_start, seven_day_end, _ = normalize_period("7d")
            seven_day_logs = fetch_audit_logs_in_range(
                store,
                start=seven_day_start,
                end=seven_day_end,
                event_type="question_allowed",
            )
            seven_day_snapshot = build_activity_snapshot(
                seven_day_logs,
                selected_department=selected_department,
                indexed_documents=indexed_documents,
                include_user_breakdown=False,
            )
            seven_day_question_df = seven_day_snapshot["question_df"]
        except Exception:
            pass
        resource_status = build_resource_status(
            queue_size=runtime_status.get("queue_waiting", 0),
            queue_max=runtime_status.get("max_queue_size", 0),
            base_dir=Path(__file__).parent,
        )

        if resource_status["warnings"]:
            st.markdown(build_warning_banner(resource_status["warnings"]), unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.markdown(f"""
            <div style="background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">Tổng truy vấn ({period_display})</div>
                <div style="font-size:28px;font-weight:800;color:#0f172a;margin-top:6px;">{snapshot['summary']['total_queries']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col2:
            st.markdown(f"""
            <div style="background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:11px;font-weight:700;color:#0f766e;text-transform:uppercase;letter-spacing:0.5px;">Latency TB</div>
                <div style="font-size:28px;font-weight:800;color:#0f766e;margin-top:6px;">{snapshot['summary']['avg_latency_ms']:.1f} ms</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col3:
            st.markdown(f"""
            <div style="background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:11px;font-weight:700;color:#2563eb;text-transform:uppercase;letter-spacing:0.5px;">Tỷ lệ có nguồn</div>
                <div style="font-size:28px;font-weight:800;color:#2563eb;margin-top:6px;">{snapshot['summary']['source_rate_pct']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col4:
            st.markdown(f"""
            <div style="background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:11px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.5px;">Số tài liệu indexed</div>
                <div style="font-size:28px;font-weight:800;color:#7c3aed;margin-top:6px;">{snapshot['summary']['indexed_documents']:,}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        col_line, col_donut = st.columns([3, 2])
        with col_line:
            st.markdown("##### Truy vấn theo giờ trong kỳ")
            hourly_df = snapshot["hourly_df"].copy()
            if period_choice == "Hôm nay":
                full_hours = pd.DataFrame({"hour": [f"{hour:02d}:00" for hour in range(24)]})
                hourly_df = full_hours.merge(hourly_df, on="hour", how="left").fillna(0)
            if not hourly_df.empty:
                st.line_chart(hourly_df.set_index("hour")["count"])
            else:
                st.info("Không có dữ liệu truy vấn trong khoảng thời gian này.")
        with col_donut:
            st.markdown("##### Phân bổ theo phòng ban")
            department_df = snapshot["department_df"]
            if not department_df.empty:
                st.markdown(
                    build_donut_html(
                        "Phân bổ truy vấn",
                        department_df["department"].tolist(),
                        department_df["count"].tolist(),
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.info("Không có dữ liệu phòng ban khớp bộ lọc.")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### Top 10 câu hỏi phổ biến (7 ngày qua)")
        if seven_day_question_df.empty:
            st.info("Chưa có dữ liệu câu hỏi trong kỳ này.")
        else:
            st.dataframe(seven_day_question_df, use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### Trạng thái tài nguyên realtime")
        ram_value = resource_status["ram_usage"]
        vram_value = resource_status["vram_usage"]
        queue_size = resource_status["queue_size"]
        queue_max = resource_status["queue_max"]
        resource_col1, resource_col2, resource_col3 = st.columns(3)
        with resource_col1:
            st.markdown((f"<div style='background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;'><div style='font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>RAM usage</div><div style='font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;'>{ram_value:.0f}%</div></div>" if ram_value is not None else "<div style='background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;'><div style='font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>RAM usage</div><div style='font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;'>N/A</div></div>"), unsafe_allow_html=True)
        with resource_col2:
            st.markdown((f"<div style='background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;'><div style='font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>VRAM usage</div><div style='font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;'>{vram_value:.0f}%</div></div>" if vram_value is not None else "<div style='background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;'><div style='font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>VRAM usage</div><div style='font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;'>N/A</div></div>"), unsafe_allow_html=True)
        with resource_col3:
            st.markdown(f"<div style='background:#ffffff;padding:16px;border:1px solid #e2e8f0;border-radius:14px;'><div style='font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>Queue size</div><div style='font-size:26px;font-weight:800;color:#0f172a;margin-top:6px;'>{queue_size}/{queue_max}</div></div>", unsafe_allow_html=True)

        backup_at = resource_status.get("last_backup_at")
        if backup_at:
            st.caption(f"Sao lưu gần nhất: {backup_at.astimezone(timezone.utc).strftime('%H:%M:%S %d/%m/%Y UTC')}")
        else:
            st.caption("Sao lưu gần nhất: chưa có dữ liệu")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### Xuất báo cáo")
        export_title = f"AI Dashboard - {period_display}"
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            try:
                excel_bytes = build_excel_bytes(snapshot)
                st.download_button(
                    "Tải Excel",
                    data=excel_bytes,
                    file_name=f"ai_dashboard_{period_choice.lower().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as exc:
                st.warning(f"Không xuất được Excel: {exc}")
        with export_col2:
            try:
                pdf_bytes = build_pdf_bytes(export_title, snapshot)
                st.download_button(
                    "Tải PDF",
                    data=pdf_bytes,
                    file_name=f"ai_dashboard_{period_choice.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                st.warning(f"Không xuất được PDF: {exc}")

    # ── TAB 5: AI USAGE REPORT ─────────────────────────────────────────────────
    elif st.session_state.navigation == "AI Report":
        if st.session_state.auth_user_role not in {"Admin", "Manager"}:
            st.error("Bạn không có quyền truy cập trang này.")
            return

        st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">📈 Báo cáo thống kê tình hình sử dụng AI</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">Tổng hợp query, phòng ban, người dùng, tài liệu phổ biến và phân bố latency.</p>', unsafe_allow_html=True)
        st.markdown("---")
        st.components.v1.html("<meta http-equiv='refresh' content='20'>", height=0)

        dept_labels = {
            "all": "Tất cả phòng ban",
            "general": "General",
            "finance": "Finance",
            "hr": "HR",
            "it": "IT",
            "legal": "Legal",
            "security": "Security",
        }

        period_label_map = {
            "Hôm nay": "today",
            "7 ngày": "7d",
            "30 ngày": "30d",
            "Tùy chỉnh": "custom",
        }
        period_choice = st.radio("Khoảng thời gian", list(period_label_map.keys()), horizontal=True, key="report_period_choice")

        custom_start = None
        custom_end = None
        if period_choice == "Tùy chỉnh":
            col_start, col_end = st.columns(2)
            with col_start:
                custom_start = st.date_input("Từ ngày", value=datetime.date.today() - datetime.timedelta(days=7), key="report_start")
            with col_end:
                custom_end = st.date_input("Đến ngày", value=datetime.date.today(), key="report_end")

        if st.session_state.auth_user_role == "Manager":
            selected_department = st.session_state.auth_department
            st.info(f"Báo cáo đang cố định theo phòng ban của bạn: {selected_department}")
        else:
            selected_department = st.selectbox(
                "Phòng ban",
                ["all", "general", "finance", "hr", "it", "legal", "security"],
                format_func=lambda value: dept_labels.get(value, value),
                key="report_department",
            )

        try:
            start_dt, end_dt, period_display = normalize_period(
                period_label_map[period_choice],
                custom_start=custom_start,
                custom_end=custom_end,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        try:
            question_logs = fetch_audit_logs_in_range(
                store,
                start=start_dt,
                end=end_dt,
                event_type="question_allowed",
            )
        except Exception as exc:
            st.error(f"Không thể đọc query log: {exc}")
            return

        try:
            indexed_documents = rag.get_stats().get("vector_store", {}).get("count", 0)
        except Exception:
            indexed_documents = 0

        is_admin = st.session_state.auth_user_role == "Admin"
        snapshot = build_activity_snapshot(
            question_logs,
            selected_department=selected_department,
            indexed_documents=indexed_documents,
            include_user_breakdown=is_admin,
        )

        report_col1, report_col2, report_col3, report_col4 = st.columns(4)
        with report_col1:
            st.metric(f"Tổng query ({period_display})", f"{snapshot['summary']['total_queries']:,}")
        with report_col2:
            st.metric("Query thành công", f"{snapshot['summary']['successful_queries']:,}")
        with report_col3:
            st.metric("Query không tìm thấy", f"{snapshot['summary']['no_source_queries']:,}")
        with report_col4:
            st.metric("Avg latency", f"{snapshot['summary']['avg_latency_ms']:.1f} ms")

        st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)
        report_left, report_right = st.columns([2, 1])
        with report_left:
            st.markdown("##### Báo cáo theo phòng ban")
            if snapshot["department_df"].empty:
                st.info("Không có dữ liệu phòng ban khớp bộ lọc.")
            else:
                st.bar_chart(snapshot["department_df"].set_index("department")["count"])
        with report_right:
            st.markdown("##### Top tài liệu được truy cập")
            if snapshot["document_df"].empty:
                st.info("Chưa có dữ liệu tài liệu.")
            else:
                st.dataframe(snapshot["document_df"], use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        col_hist, col_users = st.columns([2, 1])
        with col_hist:
            st.markdown("##### Latency distribution")
            if snapshot["latency_df"].empty:
                st.info("Chưa có dữ liệu latency.")
            else:
                st.bar_chart(snapshot["latency_df"].set_index("bucket")["count"])
        with col_users:
            st.markdown("##### Top 10 user sử dụng nhiều nhất")
            if not is_admin:
                st.info("Báo cáo theo người dùng chỉ dành cho Admin.")
            elif snapshot["user_df"].empty:
                st.info("Chưa có dữ liệu user.")
            else:
                st.dataframe(snapshot["user_df"], use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("##### Top 10 câu hỏi phổ biến")
        if snapshot["question_df"].empty:
            st.info("Chưa có dữ liệu câu hỏi.")
        else:
            st.dataframe(snapshot["question_df"], use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("##### Xuất báo cáo")
        report_title = f"AI Usage Report - {period_display}"
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            try:
                excel_bytes = build_excel_bytes(snapshot)
                st.download_button(
                    "Tải Excel",
                    data=excel_bytes,
                    file_name=f"ai_usage_report_{period_choice.lower().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as exc:
                st.warning(f"Không xuất được Excel: {exc}")
        with export_col2:
            try:
                pdf_bytes = build_pdf_bytes(report_title, snapshot)
                st.download_button(
                    "Tải PDF",
                    data=pdf_bytes,
                    file_name=f"ai_usage_report_{period_choice.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                st.warning(f"Không xuất được PDF: {exc}")

    # ── TAB 5: RBAC ADMIN ─────────────────────────────────────────────────────
    elif st.session_state.navigation == "RBAC Admin":
        if st.session_state.auth_user_role != "Admin":
            st.error("Bạn không có quyền truy cập trang này.")
            return

        render_rbac_admin_page(store)

    # ── TAB 6: SYSTEM AUDIT LOGS (Nhật ký hệ thống) ─────────────────────────────
    elif st.session_state.navigation == "Audit Log":
        if st.session_state.auth_user_role != "Admin":
            st.error("Bạn không có quyền truy cập trang này.")
            return

        st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">🛡️ Nhật ký hệ thống (Audit Log)</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">Giám sát các hoạt động bảo mật, xác thực tài khoản và hỏi đáp tài liệu.</p>', unsafe_allow_html=True)
        st.markdown("---")

        # 1. Fetch KPI Statistics
        def _get_kpi_counts(conn):
            total = conn.execute("SELECT COUNT(*) as cnt FROM audit_logs").fetchone()["cnt"]
            logins = conn.execute("SELECT COUNT(*) as cnt FROM audit_logs WHERE event = 'login'").fetchone()["cnt"]
            warnings = conn.execute("SELECT COUNT(*) as cnt FROM audit_logs WHERE event IN ('conversation_access_denied', 'message_write_denied')").fetchone()["cnt"]
            return total, logins, warnings

        try:
            kpi_total, kpi_logins, kpi_warnings = store._run_with_retry(_get_kpi_counts)
        except Exception:
            kpi_total, kpi_logins, kpi_warnings = 0, 0, 0

        # KPI Layout
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        with col_kpi1:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">📊 Tổng số hoạt động</div>
                <div style="font-size: 26px; font-weight: 700; color: #1e293b; margin-top: 6px;">{kpi_total:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_kpi2:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 11px; font-weight: 600; color: #10a37f; text-transform: uppercase; letter-spacing: 0.5px;">🔑 Đăng nhập thành công</div>
                <div style="font-size: 26px; font-weight: 700; color: #10a37f; margin-top: 6px;">{kpi_logins:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_kpi3:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 11px; font-weight: 600; color: #ef4444; text-transform: uppercase; letter-spacing: 0.5px;">🚨 Cảnh báo bảo mật</div>
                <div style="font-size: 26px; font-weight: 700; color: #ef4444; margin-top: 6px;">{kpi_warnings:,}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

        # 2. Filters card section
        st.markdown("##### 🔍 Bộ lọc tìm kiếm")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_categories = {
                "Tất cả sự kiện": None,
                "Xác thực (Auth)": ["login", "register", "logout"],
                "Hỏi đáp tài liệu (Q&A)": ["question_allowed"],
                "Bảo mật / Cấm truy cập": ["conversation_access_denied", "message_write_denied"],
                "Tải lên tài liệu (Upload)": ["document_upload"],
                "Cuộc chat & Bộ nhớ": ["conversation_create", "conversation_delete", "message_append", "summary_upsert", "user_memory_upsert"]
            }
            selected_cat_label = st.selectbox("Nhóm sự kiện", list(filter_categories.keys()))
            event_filter = filter_categories[selected_cat_label]

        with col_f2:
            email_filter = st.text_input("Tìm theo email người dùng", placeholder="ví dụ: employee@anphat.com")
            email_filter = email_filter.strip() if email_filter.strip() else None

        with col_f3:
            use_date_filter = st.checkbox("Lọc theo thời gian", value=False)
            start_date_str, end_date_str = None, None
            if use_date_filter:
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date_val = st.date_input("Từ ngày")
                with col_date2:
                    end_date_val = st.date_input("Đến ngày")
                start_date_str = start_date_val.isoformat()
                end_date_str = end_date_val.isoformat()

        # 3. Setup Pagination State
        if "audit_page" not in st.session_state:
            st.session_state.audit_page = 0
        
        filter_key = f"{selected_cat_label}_{email_filter}_{start_date_str}_{end_date_str}"
        if "last_audit_filter" not in st.session_state or st.session_state.last_audit_filter != filter_key:
            st.session_state.audit_page = 0
            st.session_state.last_audit_filter = filter_key

        limit_per_page = 20
        offset = st.session_state.audit_page * limit_per_page

        # 4. Fetch Logs from Store
        logs, total_filtered = store.get_audit_logs(
            limit=limit_per_page,
            offset=offset,
            event_type=event_filter,
            email_query=email_filter,
            start_date=start_date_str,
            end_date=end_date_str
        )

        # 5. Display Premium HTML Table
        st.markdown("""
        <style>
            .audit-table {
                width: 100%;
                border-collapse: collapse;
                margin: 16px 0;
                font-size: 13px;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                border: 1px solid #e2e8f0;
            }
            .audit-table th {
                background-color: #f8fafc;
                color: #475569;
                text-align: left;
                padding: 12px 16px;
                font-weight: 600;
                border-bottom: 1px solid #e2e8f0;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            .audit-table td {
                padding: 12px 16px;
                border-bottom: 1px solid #f1f5f9;
                color: #334155;
            }
            .audit-table tr:hover {
                background-color: #f8fafc;
            }
            .audit-badge {
                display: inline-block;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                border-radius: 9999px;
                text-transform: uppercase;
                text-align: center;
            }
            .badge-success { background-color: #e7f5ee; color: #10a37f; }
            .badge-info { background-color: #e0f2fe; color: #0284c7; }
            .badge-warning { background-color: #fef3c7; color: #d97706; }
            .badge-danger { background-color: #fee2e2; color: #ef4444; }
            .badge-neutral { background-color: #f1f5f9; color: #475569; }
        </style>
        """, unsafe_allow_html=True)

        if not logs:
            st.info("Không tìm thấy nhật ký hệ thống nào khớp với điều kiện tìm kiếm.")
        else:
            rows_html = []
            for log in logs:
                event = log["event"]
                user_email = log["user_email"] or "Hệ thống / Ẩn danh"
                created_at = log["created_at"].strftime("%H:%M:%S • %d/%m/%Y")
                
                details_str = json.dumps(log["details"])
                details_preview = details_str[:85] + "..." if len(details_str) > 85 else details_str
                
                badge_class = "badge-neutral"
                if event in ["login", "register", "logout"]:
                    badge_class = "badge-success"
                elif event in ["document_upload"]:
                    badge_class = "badge-info"
                elif event in ["conversation_access_denied", "message_write_denied"]:
                    badge_class = "badge-danger"
                elif event in ["question_allowed"]:
                    badge_class = "badge-info"
                    
                rows_html.append(
                    f'<tr>'
                    f'<td><span class="audit-badge {badge_class}">{event}</span></td>'
                    f'<td><strong>{user_email}</strong></td>'
                    f'<td style="color: #64748b;">{created_at}</td>'
                    f'<td style="font-family: monospace; font-size: 12px; color: #475569;">{details_preview}</td>'
                    f'</tr>'
                )
                
            table_html = (
                '<table class="audit-table">'
                '<thead>'
                '<tr>'
                '<th style="width: 25%;">Sự kiện</th>'
                '<th style="width: 25%;">Người dùng</th>'
                '<th style="width: 20%;">Thời gian</th>'
                '<th style="width: 30%;">Chi tiết payload</th>'
                '</tr>'
                '</thead>'
                '<tbody>'
                f'{"".join(rows_html)}'
                '</tbody>'
                '</table>'
            )
            st.markdown(table_html, unsafe_allow_html=True)

            # 6. Pagination UI
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            total_pages = max(1, (total_filtered + limit_per_page - 1) // limit_per_page)
            
            with col_nav1:
                if st.button("◀ Trang trước", disabled=st.session_state.audit_page == 0, use_container_width=True):
                    st.session_state.audit_page -= 1
                    st.rerun()
            with col_nav2:
                st.markdown(f"<div style='text-align: center; line-height: 38px; font-weight: 500;'>Trang {st.session_state.audit_page + 1} / {total_pages} (Tổng {total_filtered} bản ghi)</div>", unsafe_allow_html=True)
            with col_nav3:
                if st.button("Trang sau ▶", disabled=st.session_state.audit_page >= total_pages - 1, use_container_width=True):
                    st.session_state.audit_page += 1
                    st.rerun()

            # 7. Interactive JSON detail view
            st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📁 Chi tiết bản ghi (Payload JSON)")
            st.caption("Mở rộng từng dòng để xem đầy đủ thông tin chi tiết của log kiểm toán:")
            for log in logs:
                event = log["event"]
                user_email = log["user_email"] or "Hệ thống / Ẩn danh"
                created_at = log["created_at"].strftime("%H:%M:%S • %d/%m/%Y")
                with st.expander(f"🔍 [{event.upper()}] {user_email} tại {created_at}"):
                    st.json(log["details"])

            # 8. Export CSV Section
            st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📥 Xuất báo cáo")
            try:
                # Fetch up to 5000 rows matching current filters
                export_logs, _ = store.get_audit_logs(
                    limit=5000,
                    offset=0,
                    event_type=event_filter,
                    email_query=email_filter,
                    start_date=start_date_str,
                    end_date=end_date_str
                )
                
                import io
                import csv
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["ID", "Sự kiện", "Email", "Quyền", "Thời gian", "Chi tiết Payload"])
                for log in export_logs:
                    writer.writerow([
                        log["id"],
                        log["event"],
                        log["user_email"] or "",
                        log["user_role"] or "",
                        log["created_at"].isoformat(),
                        json.dumps(log["details"])
                    ])
                
                st.download_button(
                    label="Tải báo cáo CSV kiểm toán (Excel Compatible)",
                    data=csv_buffer.getvalue().encode('utf-8-sig'),
                    file_name=f"audit_logs_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Lỗi khi chuẩn bị dữ liệu xuất CSV: {e}")


if __name__ == "__main__":
    main()
