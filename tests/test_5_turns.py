"""
Test 5 câu liên tiếp — Kiểm tra Memory, Rewrite, Context Recall
Xuất kết quả ra Markdown để review.
"""
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "d:/K2N3/Quản lý dự án/Project")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src.rag.rag_pipeline import RAGPipeline
from src.storage.chat_store import ChatStore
from app import update_rolling_summary, extract_selected_user_memories, build_system_prompt

# ──────────────────────────────────────────────
# Kịch bản 5 câu — thiết kế theo cascade context
# ──────────────────────────────────────────────
TURNS = [
    {
        "id": 1,
        "label": "Thiết lập context + Phong cách ngắn gọn",
        "goal": "Lưu memory: Manager, TP.HCM, phong cách ngắn gọn. Trả về đúng 2.000.000 VND/đêm.",
        "question": (
            "Tôi là nhân viên cấp Manager đi công tác tại TP.HCM. "
            "Hạn mức tối đa cho phòng khách sạn của tôi là bao nhiêu? "
            "Hãy trả lời cực kỳ ngắn gọn và đi thẳng vào con số."
        ),
        "expected_keywords": ["2.000.000", "VND", "đêm"],  # 2,000,000 also accepted (normalized)
        "checks": ["memory_extract", "sources_travel_policy"],
    },
    {
        "id": 2,
        "label": "Đại từ mơ hồ: 'ở đó' + 'Nó'",
        "goal": "Query Rewrite: 'ở đó' → TP.HCM, 'Nó' → phụ cấp ăn uống → tìm đúng con số.",
        "question": "Thế còn phụ cấp ăn uống ở đó thì sao? Nó là bao nhiêu?",
        "expected_keywords": ["350.000", "VND", "ngày"],
        "checks": ["rewrite_triggered", "sources_travel_policy"],
    },
    {
        "id": 3,
        "label": "Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ",
        "goal": "Rewrite: 'hạn mức này' → hạn mức công tác. Trả về đúng chức danh phê duyệt.",
        "question": "Nếu tôi chi tiêu vượt quá hạn mức này thì ai sẽ phê duyệt ngoại lệ?",
        "expected_keywords": ["quản lý", "phê duyệt"],
        "checks": ["rewrite_triggered"],
    },
    {
        "id": 4,
        "label": "Memory Recall cấp bậc + Chính sách bay",
        "goal": "Nhớ lại 'Manager' từ memory. Trả lời đúng: chuyến bay <4h → hạng phổ thông.",
        "question": (
            "Nãy tôi nói tôi ở cấp bậc nào ấy nhỉ? "
            "Cấp đó đi chuyến bay nội địa dưới 4 tiếng thì được đi khoang nào?"
        ),
        "expected_keywords": ["Manager", "phổ thông"],  # hạng phổ thông OR khoang phổ thông
        "checks": ["memory_recall", "rewrite_triggered"],
    },
    {
        "id": 5,
        "label": "Thời hạn hoàn tiền sau chuyến công tác đó",
        "goal": "Rewrite: 'chuyến công tác đó' → chuyến công tác TP.HCM. Tìm deadline claim expense.",
        "question": (
            "Sau chuyến công tác đó, tôi cần nộp hồ sơ hoàn tiền "
            "trong bao nhiêu ngày làm việc?"
        ),
        "expected_keywords": ["ngày làm việc", "hoàn ứng"],
        "checks": ["rewrite_triggered", "sources_travel_policy"],
    },
]

REPORT_PATH = Path("d:/K2N3/Quản lý dự án/Project/evaluation/memory_context_test_5turns.md")


def detect_rewrite(original: str, rewritten: str) -> bool:
    return bool(rewritten) and rewritten.strip().lower() != original.strip().lower()


def _normalize_number(text: str) -> str:
    """Normalize Vietnamese/English number separators for comparison.
    Converts both '2,000,000' and '2.000.000' to '2000000'.
    """
    import re
    return re.sub(r'[.,](?=\d{3})', '', text)


def check_keywords(text: str, keywords: list[str]) -> dict:
    """Check keywords in answer, normalizing number formats."""
    results = {}
    text_normalized = _normalize_number(text.lower())
    for kw in keywords:
        kw_normalized = _normalize_number(kw.lower())
        # Direct match OR normalized number match
        results[kw] = kw.lower() in text.lower() or kw_normalized in text_normalized
    return results


def check_sources(sources: list, target_doc="travel_expense_policy"):
    return any(target_doc in str(s) for s in sources)


def check_cjk(text: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)


def run_test():
    store = ChatStore()
    rag = RAGPipeline()

    email = "test5turns@anphat.com"

    def _clear(conn):
        conn.execute("DELETE FROM users WHERE email = %s", (email,))
    store._run_with_retry(_clear)

    user_id = store.register_user(email, "pass1234")
    conv_id = store.create_conversation(user_id, "Test 5 Turns Memory Context")

    chat_messages = []
    turn_results = []

    print("=" * 80)
    print(f"🚀 BẮT ĐẦU TEST 5 TURNS — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for turn in TURNS:
        idx = turn["id"]
        question = turn["question"]
        t_start = time.time()

        print(f"\n{'='*80}")
        print(f"🔹 TURN {idx}: {turn['label']}")
        print(f"   Q: {question}")
        print("=" * 80)

        # Load context
        summary = store.get_conversation_summary(user_id, conv_id)
        user_memories = store.list_user_memories(user_id, limit=12)
        system_prompt = build_system_prompt(summary, user_memories)

        print(f"🔸 Rolling Summary: {summary or '(None)'}")
        print(f"🔸 Memory count: {len(user_memories)}")

        store.append_message(user_id, conv_id, "user", question)
        chat_messages.append({"role": "user", "content": question})

        # Query RAG
        print("🤖 [RAG] Querying...")
        res = rag.query(
            question=question,
            k=6,
            system_prompt=system_prompt,
            chat_history=chat_messages[:-1],
            rolling_summary=summary,
        )

        answer = res.get("answer", "")
        rewritten = res.get("rewritten_query", "")
        sources = res.get("sources", [])
        elapsed = round(time.time() - t_start, 1)

        rewrite_triggered = detect_rewrite(question, rewritten)
        rewrite_expected = "rewrite_triggered" in turn["checks"]
        rewrite_pass = (rewrite_triggered == rewrite_expected)
        kw_check = check_keywords(answer, turn["expected_keywords"])
        source_ok = check_sources(sources)
        kw_pass = all(kw_check.values())

        print(f"🔄 Rewrite triggered: {rewrite_triggered} (Expected: {rewrite_expected}) -> Pass: {rewrite_pass}")
        if rewrite_triggered:
            print(f"   → '{rewritten}'")
        print(f"📄 Sources: {sources[:3]}")
        print(f"💬 Answer (preview): {answer[:300]}")
        print(f"✅ Keywords OK: {kw_check}")
        print(f"⏱  Elapsed: {elapsed}s")

        # Save
        store.append_message(user_id, conv_id, "assistant", answer, sources)
        chat_messages.append({"role": "assistant", "content": answer})

        # Update memory & summary
        new_summary = update_rolling_summary(rag, summary, chat_messages)
        store.upsert_conversation_summary(user_id, conv_id, new_summary)

        extracted = extract_selected_user_memories(rag, chat_messages)
        has_cjk = any(check_cjk(m.get("content", "")) for m in extracted)
        if extracted:
            store.upsert_user_memories(user_id, extracted)
            print(f"🧠 Extracted {len(extracted)} memories | CJK detected: {has_cjk}")

        turn_results.append({
            "id": idx,
            "label": turn["label"],
            "goal": turn["goal"],
            "question": question,
            "rewrite_triggered": rewrite_triggered,
            "rewrite_pass": rewrite_pass,
            "rewritten_query": rewritten,
            "answer": answer,
            "sources": sources[:3],
            "source_ok": source_ok,
            "kw_check": kw_check,
            "kw_pass": kw_pass,
            "memories_extracted": len(extracted),
            "cjk_detected": has_cjk,
            "elapsed_s": elapsed,
            "new_summary": new_summary,
        })

        time.sleep(1)

    # ── Write Markdown Report ──
    write_md_report(turn_results)
    print(f"\n📄 Report saved → {REPORT_PATH}")


def verdict_icon(ok: bool) -> str:
    return "✅" if ok else "❌"


def write_md_report(results: list):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# 🧪 Memory Context Test — 5 Turns",
        f"",
        f"**Chạy lúc:** {now}  ",
        f"**Mục tiêu:** Kiểm tra Memory, Query Rewriting, và Context Recall qua 5 lượt hội thoại liên tiếp.  ",
        f"",
        f"---",
        f"",
    ]

    # Summary table
    lines += [
        "## 📊 Bảng Tổng Hợp",
        "",
        "| Turn | Mục tiêu | Rewrite | Source OK | Keywords | CJK Bug | Thời gian |",
        "|------|----------|---------|-----------|----------|---------|-----------|",
    ]

    for r in results:
        lines.append(
            f"| {r['id']} | {r['label']} "
            f"| {verdict_icon(r['rewrite_pass'])} "
            f"| {verdict_icon(r['source_ok'])} "
            f"| {verdict_icon(r['kw_pass'])} "
            f"| {verdict_icon(not r['cjk_detected'])} "
            f"| {r['elapsed_s']}s |"
        )

    # Overall score
    total = len(results)
    rewrite_ok = sum(1 for r in results if r["rewrite_pass"])
    source_ok = sum(1 for r in results if r["source_ok"])
    kw_ok = sum(1 for r in results if r["kw_pass"])
    no_cjk = sum(1 for r in results if not r["cjk_detected"])

    lines += [
        "",
        f"**Tổng hợp:** Rewrite {rewrite_ok}/{total} | Source {source_ok}/{total} | Keywords {kw_ok}/{total} | CJK-Free {no_cjk}/{total}",
        "",
        "---",
        "",
    ]

    # Detail per turn
    lines.append("## 📋 Chi Tiết Từng Turn")
    lines.append("")

    for r in results:
        kw_detail = " | ".join(
            f"`{k}` {verdict_icon(v)}" for k, v in r["kw_check"].items()
        )
        lines += [
            f"### Turn {r['id']} — {r['label']}",
            f"",
            f"> **Mục tiêu:** {r['goal']}",
            f"",
            f"**❓ Câu hỏi:**",
            f"> {r['question']}",
            f"",
            f"**🔄 Query Rewrite:** {verdict_icon(r['rewrite_triggered'])}",
        ]
        if r["rewritten_query"] and r["rewrite_triggered"]:
            lines.append(f"> _{r['rewritten_query']}_")
        lines += [
            f"",
            f"**📄 Sources:** `{'`, `'.join(str(s) for s in r['sources']) or 'N/A'}`  ",
            f"**✅ Source từ travel_expense_policy:** {verdict_icon(r['source_ok'])}  ",
            f"**🔑 Keywords:** {kw_detail}  ",
            f"**🧠 Memories extracted:** {r['memories_extracted']}  ",
            f"**🈲 CJK Bug:** {verdict_icon(not r['cjk_detected'])} (không có tiếng Trung)  ",
            f"**⏱ Thời gian:** {r['elapsed_s']}s",
            f"",
            f"**💬 Câu trả lời:**",
            f"",
            f"```",
            r["answer"].strip(),
            f"```",
            f"",
            f"**📝 Rolling Summary sau turn này:**",
            f"> {r['new_summary'] or '(Chưa có)'}",
            f"",
            "---",
            "",
        ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run_test()
