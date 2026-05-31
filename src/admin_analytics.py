"""Analytics helpers for the AI dashboard and usage reports."""

from __future__ import annotations

import ctypes
import datetime as dt
import html
import io
import json
import os
import shutil
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except Exception:  # pragma: no cover - optional dependency
    colors = None
    A4 = landscape = getSampleStyleSheet = cm = None  # type: ignore[assignment]
    pdfmetrics = TTFont = None  # type: ignore[assignment]
    PageBreak = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None  # type: ignore[assignment]


DEFAULT_DASHBOARD_COLORS = [
    "#0f766e",
    "#2563eb",
    "#f59e0b",
    "#7c3aed",
    "#ef4444",
    "#14b8a6",
    "#0ea5e9",
    "#84cc16",
]


def _register_pdf_fonts() -> tuple[str, str]:
    if pdfmetrics is None or TTFont is None:
        return "Helvetica", "Helvetica-Bold"

    normal_name = "AppUnicode"
    bold_name = "AppUnicode-Bold"
    font_pairs = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/ARIALUNI.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]

    for normal_path, bold_path in font_pairs:
        if Path(normal_path).exists():
            try:
                pdfmetrics.registerFont(TTFont(normal_name, normal_path))
                if Path(bold_path).exists():
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                else:
                    bold_name = normal_name
                return normal_name, bold_name
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def _apply_pdf_font_styles(styles: Any, font_name: str, bold_font_name: str) -> None:
    for style_name in ("Normal", "BodyText"):
        if style_name in styles:
            styles[style_name].fontName = font_name
    for style_name in ("Title", "Heading1", "Heading2", "Heading3"):
        if style_name in styles:
            styles[style_name].fontName = bold_font_name


def normalize_period(
    period: str,
    *,
    custom_start: Optional[dt.date] = None,
    custom_end: Optional[dt.date] = None,
    now: Optional[dt.datetime] = None,
) -> tuple[dt.datetime, dt.datetime, str]:
    """Resolve a dashboard time window.

    Returns UTC-aware datetimes. The end timestamp is exclusive.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    period = (period or "today").lower()

    if period == "today":
        start = now - dt.timedelta(days=1)
        label = "Hôm nay"
    elif period == "7d":
        start = now - dt.timedelta(days=7)
        label = "7 ngày"
    elif period == "30d":
        start = now - dt.timedelta(days=30)
        label = "30 ngày"
    else:
        if not custom_start or not custom_end:
            raise ValueError("Phải chọn ngày bắt đầu và kết thúc cho bộ lọc tùy chỉnh.")
        start = dt.datetime.combine(custom_start, dt.time.min, tzinfo=dt.timezone.utc)
        end = dt.datetime.combine(custom_end, dt.time.max, tzinfo=dt.timezone.utc)
        return start, end, "Tùy chỉnh"

    return start, now, label


def _to_timezone_aware(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min, tzinfo=dt.timezone.utc)
    if isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value)
        except ValueError:
            parsed = dt.datetime.strptime(value, "%Y-%m-%d")
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    raise TypeError(f"Không thể chuyển {type(value)!r} thành datetime.")


def _safe_text(value: Any, limit: int = 220) -> str:
    text = str(value or "").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _extract_details(log: dict[str, Any]) -> dict[str, Any]:
    details = log.get("details") or {}
    if isinstance(details, str):
        try:
            return json.loads(details)
        except Exception:
            return {"raw": details}
    if isinstance(details, dict):
        return details
    return {}


def _extract_department(log: dict[str, Any]) -> str:
    details = _extract_details(log)
    department = details.get("department") or log.get("department") or "general"
    return str(department).strip().lower() or "general"


def _extract_question_text(log: dict[str, Any]) -> str:
    details = _extract_details(log)
    question = (
        details.get("question_text")
        or details.get("question_preview")
        or details.get("query")
        or details.get("prompt")
        or ""
    )
    return _safe_text(question, 180)


def _extract_sources(log: dict[str, Any]) -> list[str]:
    details = _extract_details(log)
    raw_sources = details.get("sources") or details.get("source_files") or []
    source_names: list[str] = []
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if isinstance(item, str):
                name = _safe_text(item, 120)
            elif isinstance(item, dict):
                name = _safe_text(
                    item.get("metadata", {}).get("file_name")
                    or item.get("metadata", {}).get("source")
                    or item.get("file_name")
                    or item.get("source")
                    or item.get("name"),
                    120,
                )
            else:
                name = _safe_text(item, 120)
            if name:
                source_names.append(name)
    elif raw_sources:
        source_names.append(_safe_text(raw_sources, 120))
    return source_names


def _extract_sources_count(log: dict[str, Any]) -> int:
    details = _extract_details(log)
    raw_count = details.get("sources_count")
    if raw_count is None:
        raw_count = details.get("source_count")
    try:
        return max(0, int(raw_count))
    except (TypeError, ValueError):
        return len(_extract_sources(log))


def _extract_latency_ms(log: dict[str, Any]) -> float:
    details = _extract_details(log)
    timing = details.get("timing") if isinstance(details.get("timing"), dict) else {}
    candidates = [
        details.get("latency_ms"),
        details.get("total_ms"),
        details.get("response_ms"),
        timing.get("total_ms"),
        timing.get("ttft_ms"),
    ]
    for candidate in candidates:
        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return value
    return 0.0


def _extract_user_email(log: dict[str, Any]) -> str:
    email = log.get("user_email") or ""
    return str(email).strip().lower() or "unknown"


def fetch_audit_logs_in_range(
    store: Any,
    *,
    start: dt.datetime,
    end: dt.datetime,
    event_type: Optional[str | list[str]] = "question_allowed",
    email_query: Optional[str] = None,
    page_size: int = 200,
) -> list[dict[str, Any]]:
    """Fetch all audit logs in a time range using the store's paginated API."""
    start_date = start.date().isoformat()
    end_date = end.date().isoformat()
    logs: list[dict[str, Any]] = []
    offset = 0

    while True:
        page, total = store.get_audit_logs(
            limit=page_size,
            offset=offset,
            event_type=event_type,
            email_query=email_query,
            start_date=start_date,
            end_date=end_date,
        )
        logs.extend(page)
        offset += len(page)
        if offset >= total or not page:
            break

    return logs


def build_activity_snapshot(
    logs: Iterable[dict[str, Any]],
    *,
    selected_department: str = "all",
    indexed_documents: int = 0,
    include_user_breakdown: bool = False,
) -> dict[str, Any]:
    """Aggregate the question log stream into dashboard/report friendly tables."""
    normalized_department = (selected_department or "all").strip().lower()
    question_logs = [log for log in logs if log.get("event") == "question_allowed"]

    if normalized_department not in {"all", "", "tất cả", "tat ca"}:
        question_logs = [log for log in question_logs if _extract_department(log) == normalized_department]

    total_queries = len(question_logs)
    queries_with_sources = [log for log in question_logs if _extract_sources_count(log) > 0]
    no_source_queries = total_queries - len(queries_with_sources)
    latencies = [
        latency
        for latency in (_extract_latency_ms(log) for log in question_logs)
        if latency >= 0
    ]

    start_hour = None
    end_hour = None
    if question_logs:
        times = [log.get("created_at") for log in question_logs if log.get("created_at")]
        if times:
            start_hour = min(times)
            end_hour = max(times)

    hourly_counter: Counter[str] = Counter()
    department_counter: Counter[str] = Counter()
    question_counter: Counter[str] = Counter()
    document_counter: Counter[str] = Counter()
    user_counter: Counter[str] = Counter()
    source_rate_counter = 0

    for log in question_logs:
        created_at = log.get("created_at")
        if isinstance(created_at, dt.datetime):
            hourly_counter[created_at.astimezone(dt.timezone.utc).strftime("%H:00")] += 1
        department_counter[_extract_department(log)] += 1
        question_counter[_extract_question_text(log)] += 1
        user_counter[_extract_user_email(log)] += 1
        sources = _extract_sources(log)
        if sources:
            source_rate_counter += 1
        for source_name in sources:
            document_counter[source_name] += 1

    hourly_rows = [
        {"hour": hour, "count": hourly_counter.get(hour, 0)}
        for hour in sorted(hourly_counter.keys())
    ]
    department_rows = [
        {"department": department, "count": count}
        for department, count in department_counter.most_common()
    ]
    question_rows = [
        {"question": question, "count": count}
        for question, count in question_counter.most_common(10)
    ]
    document_rows = [
        {"document": document, "count": count}
        for document, count in document_counter.most_common(10)
    ]
    user_rows = [
        {"user": user, "count": count}
        for user, count in user_counter.most_common(10)
    ]

    latency_bins = build_latency_histogram(latencies)

    summary = {
        "total_queries": total_queries,
        "successful_queries": len(queries_with_sources),
        "no_source_queries": no_source_queries,
        "avg_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
        "source_rate_pct": round((source_rate_counter / total_queries) * 100, 1) if total_queries else 0.0,
        "indexed_documents": indexed_documents,
    }

    result: dict[str, Any] = {
        "summary": summary,
        "hourly_df": pd.DataFrame(hourly_rows),
        "department_df": pd.DataFrame(department_rows),
        "question_df": pd.DataFrame(question_rows),
        "document_df": pd.DataFrame(document_rows),
        "latency_df": latency_bins,
        "user_df": pd.DataFrame(user_rows),
        "raw_logs": question_logs,
        "selected_department": normalized_department,
        "period_start": start_hour,
        "period_end": end_hour,
    }

    if include_user_breakdown:
        result["user_df"] = pd.DataFrame(user_rows)
    else:
        result["user_df"] = pd.DataFrame(user_rows[:0])

    return result


def build_latency_histogram(values: list[float], bins: int = 8) -> pd.DataFrame:
    """Build a histogram dataframe for latency visualization."""
    if not values:
        return pd.DataFrame(columns=["bucket", "count"])

    if len(set(values)) == 1:
        return pd.DataFrame(
            [{"bucket": f"{values[0]:.0f} ms", "count": len(values)}]
        )

    bin_count = max(4, min(bins, len(values)))
    counts, edges = np.histogram(values, bins=bin_count)
    rows = []
    for index, count in enumerate(counts):
        left = edges[index]
        right = edges[index + 1]
        rows.append({"bucket": f"{left:.0f}-{right:.0f} ms", "count": int(count)})
    return pd.DataFrame(rows)


def build_donut_html(
    title: str,
    labels: list[str],
    values: list[int | float],
    *,
    colors_palette: Optional[list[str]] = None,
) -> str:
    """Create a lightweight donut chart using CSS conic-gradient."""
    palette = colors_palette or DEFAULT_DASHBOARD_COLORS
    total = float(sum(values)) if values else 0.0
    if total <= 0:
        return f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:18px;">
            <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:8px;">{html.escape(title)}</div>
            <div style="color:#64748b;font-size:13px;">Không có dữ liệu để hiển thị.</div>
        </div>
        """

    segments = []
    start = 0.0
    for index, value in enumerate(values):
        percent = (float(value) / total) * 100.0
        end = start + percent
        color = palette[index % len(palette)]
        segments.append(f"{color} {start:.2f}% {end:.2f}%")
        start = end

    legend_items = []
    for index, (label, value) in enumerate(zip(labels, values)):
        color = palette[index % len(palette)]
        pct = (float(value) / total) * 100.0
        legend_items.append(
            f"""
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:8px;min-width:0;">
                    <span style="width:10px;height:10px;border-radius:999px;background:{color};display:inline-block;flex:0 0 auto;"></span>
                    <span style="font-size:13px;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{html.escape(str(label))}</span>
                </div>
                <div style="font-size:13px;font-weight:600;color:#0f172a;">{int(value)} ({pct:.1f}%)</div>
            </div>
            """
        )

    return f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">{html.escape(title)}</div>
        <div style="display:grid;grid-template-columns:180px 1fr;gap:18px;align-items:center;">
            <div style="display:flex;align-items:center;justify-content:center;">
                <div style="position:relative;width:160px;height:160px;border-radius:50%;background:conic-gradient({', '.join(segments)});">
                    <div style="position:absolute;inset:28px;background:#ffffff;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center;border:1px solid #e2e8f0;">
                        <div style="font-size:22px;font-weight:700;color:#0f172a;">{int(total)}</div>
                        <div style="font-size:11px;color:#64748b;letter-spacing:0.04em;text-transform:uppercase;">Tổng</div>
                    </div>
                </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:2px;">{''.join(legend_items)}</div>
        </div>
    </div>
    """


def get_system_ram_usage_percent() -> Optional[float]:
    """Return Windows RAM usage percentage if available."""
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return float(state.dwMemoryLoad)
    except Exception:
        return None
    return None


def get_vram_usage_percent() -> Optional[float]:
    """Return the highest GPU memory usage percentage from nvidia-smi if available."""
    if shutil.which("nvidia-smi") is None:
        return None

    command = [
        "nvidia-smi",
        "--query-gpu=memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=3)
    except Exception:
        return None

    percentages: list[float] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",") if part.strip()]
        if len(parts) != 2:
            continue
        try:
            used = float(parts[0])
            total = float(parts[1])
        except ValueError:
            continue
        if total > 0:
            percentages.append((used / total) * 100.0)

    return max(percentages) if percentages else None


def get_last_backup_timestamp(base_dir: Path) -> Optional[dt.datetime]:
    """Read the most recent backup timestamp from a local status file or environment."""
    candidates = [
        base_dir / "data" / "backup_status.json",
        base_dir / "logs" / "backup_status.json",
    ]
    env_value = os.getenv("LAST_BACKUP_AT")
    if env_value:
        try:
            parsed = dt.datetime.fromisoformat(env_value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass

    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw_value = payload.get("last_backup_at") or payload.get("timestamp")
        if not raw_value:
            continue
        try:
            parsed = dt.datetime.fromisoformat(str(raw_value))
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)

    return None


def build_resource_status(
    *,
    queue_size: int,
    queue_max: int,
    base_dir: Path,
) -> dict[str, Any]:
    """Collect realtime-ish system status for the dashboard."""
    ram_usage = get_system_ram_usage_percent()
    vram_usage = get_vram_usage_percent()
    last_backup_at = get_last_backup_timestamp(base_dir)
    backup_age_hours = None
    backup_warning = None

    if last_backup_at is not None:
        backup_age_hours = round(
            (dt.datetime.now(dt.timezone.utc) - last_backup_at.astimezone(dt.timezone.utc)).total_seconds() / 3600.0,
            1,
        )
        if backup_age_hours > 24:
            backup_warning = f"Chưa backup trong {backup_age_hours:.1f} giờ"

    warnings = []
    if vram_usage is not None and vram_usage > 80:
        warnings.append(f"VRAM đang ở mức {vram_usage:.0f}%")
    if queue_size > 30:
        warnings.append(f"Queue vượt ngưỡng {queue_size} req")
    if backup_warning:
        warnings.append(backup_warning)

    return {
        "ram_usage": ram_usage,
        "vram_usage": vram_usage,
        "queue_size": queue_size,
        "queue_max": queue_max,
        "last_backup_at": last_backup_at,
        "backup_age_hours": backup_age_hours,
        "backup_warning": backup_warning,
        "warnings": warnings,
    }


def build_export_frames(snapshot: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Convert a snapshot into dataframes for spreadsheet export."""
    frames = {
        "Summary": pd.DataFrame(
            [
                {
                    "Metric": "Tổng truy vấn",
                    "Value": snapshot["summary"]["total_queries"],
                },
                {
                    "Metric": "Query thành công",
                    "Value": snapshot["summary"]["successful_queries"],
                },
                {
                    "Metric": "Query không tìm thấy",
                    "Value": snapshot["summary"]["no_source_queries"],
                },
                {
                    "Metric": "Avg latency (ms)",
                    "Value": snapshot["summary"]["avg_latency_ms"],
                },
                {
                    "Metric": "Tỷ lệ có nguồn (%)",
                    "Value": snapshot["summary"]["source_rate_pct"],
                },
                {
                    "Metric": "Số tài liệu indexed",
                    "Value": snapshot["summary"]["indexed_documents"],
                },
            ]
        ),
        "Hourly": snapshot.get("hourly_df", pd.DataFrame()),
        "ByDepartment": snapshot.get("department_df", pd.DataFrame()),
        "TopQuestions": snapshot.get("question_df", pd.DataFrame()),
        "TopDocuments": snapshot.get("document_df", pd.DataFrame()),
        "Latency": snapshot.get("latency_df", pd.DataFrame()),
        "TopUsers": snapshot.get("user_df", pd.DataFrame()),
    }
    return frames


def build_excel_bytes(snapshot: dict[str, Any]) -> bytes:
    """Export analytics tables to an Excel workbook."""
    buffer = io.BytesIO()
    frames = build_export_frames(snapshot)

    writer_engine = None
    for engine in ("openpyxl", "xlsxwriter"):
        try:
            with pd.ExcelWriter(buffer, engine=engine) as writer:
                for sheet_name, frame in frames.items():
                    if frame is None or frame.empty:
                        frame = pd.DataFrame([{"message": "Không có dữ liệu"}])
                    frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            writer_engine = engine
            break
        except ImportError:
            continue

    if writer_engine is None:
        raise RuntimeError("Chưa cài thư viện hỗ trợ xuất Excel (openpyxl hoặc xlsxwriter).")

    return buffer.getvalue()


def build_pdf_bytes(title: str, snapshot: dict[str, Any]) -> bytes:
    """Export analytics tables to a PDF report."""
    if SimpleDocTemplate is None:
        raise RuntimeError("Thư viện reportlab chưa sẵn sàng để xuất PDF.")

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.1 * cm,
        rightMargin=1.1 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
    )
    styles = getSampleStyleSheet()
    font_name, bold_font_name = _register_pdf_fonts()
    _apply_pdf_font_styles(styles, font_name, bold_font_name)
    story: list[Any] = []

    story.append(Paragraph(html.escape(title), styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))

    summary_rows = [["Chỉ số", "Giá trị"]]
    for metric, value in [
        ("Tổng truy vấn", snapshot["summary"]["total_queries"]),
        ("Query thành công", snapshot["summary"]["successful_queries"]),
        ("Query không tìm thấy", snapshot["summary"]["no_source_queries"]),
        ("Avg latency (ms)", snapshot["summary"]["avg_latency_ms"]),
        ("Tỷ lệ có nguồn (%)", snapshot["summary"]["source_rate_pct"]),
        ("Số tài liệu indexed", snapshot["summary"]["indexed_documents"]),
    ]:
        summary_rows.append([metric, str(value)])
    summary_table = Table(summary_rows, colWidths=[8 * cm, 6 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTNAME", (0, 0), (-1, 0), bold_font_name),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * cm))

    for sheet_title, frame in [
        ("Truy vấn theo giờ", snapshot.get("hourly_df", pd.DataFrame())),
        ("Theo phòng ban", snapshot.get("department_df", pd.DataFrame())),
        ("Top câu hỏi", snapshot.get("question_df", pd.DataFrame())),
        ("Top tài liệu", snapshot.get("document_df", pd.DataFrame())),
        ("Latency distribution", snapshot.get("latency_df", pd.DataFrame())),
        ("Top user", snapshot.get("user_df", pd.DataFrame())),
    ]:
        story.append(Paragraph(html.escape(sheet_title), styles["Heading2"]))
        if frame is None or frame.empty:
            story.append(Paragraph("Không có dữ liệu.", styles["BodyText"]))
        else:
            rows = [list(frame.columns)] + frame.astype(str).values.tolist()
            table = Table(rows, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTNAME", (0, 0), (-1, 0), bold_font_name),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(table)
        story.append(Spacer(1, 0.35 * cm))

    document.build(story)
    return buffer.getvalue()


def build_warning_banner(warnings: list[str]) -> str:
    """Render a banner for system alerts."""
    if not warnings:
        return ""
    items = "".join(f"<li>{html.escape(item)}</li>" for item in warnings)
    return f"""
    <div style="background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;padding:14px 16px;border-radius:14px;">
        <div style="font-size:13px;font-weight:700;margin-bottom:6px;">Cảnh báo realtime</div>
        <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.6;">{items}</ul>
    </div>
    """
