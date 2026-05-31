"""Admin RBAC and audit management pages for the Streamlit app."""

from __future__ import annotations

import datetime as dt
import html
import io
import json
from typing import Any

import pandas as pd
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:  # pragma: no cover - optional dependency
    colors = None
    A4 = landscape = getSampleStyleSheet = cm = None  # type: ignore[assignment]
    Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None  # type: ignore[assignment]

from src.config import POSTGRES_CONNECTION_STRING
from src.storage import ChatStore

ROLE_OPTIONS = ["Admin", "HR", "Finance", "Legal", "Viewer", "Employee"]
DEPARTMENT_OPTIONS = ["general", "finance", "hr", "it", "legal", "security"]
SEVERITY_OPTIONS = ["Info", "Warning", "Critical"]


def _severity_for_event(event: str) -> str:
    event = (event or "").strip().lower()
    if event in {"message_write_denied", "conversation_access_denied", "user_force_logout"}:
        return "Critical"
    if event in {"user_status_change", "user_password_reset", "rbac_group_delete", "rbac_matrix_update"}:
        return "Warning"
    return "Info"


def _audit_export_excel(logs: list[dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    frame = pd.DataFrame(logs)
    if frame.empty:
        frame = pd.DataFrame([{"message": "Không có dữ liệu"}])
    excel_engine = None
    for candidate in ("openpyxl", "xlsxwriter"):
        try:
            __import__(candidate)
            excel_engine = candidate
            break
        except Exception:
            continue
    if excel_engine is None:
        raise RuntimeError("Không tìm thấy engine xuất Excel. Hãy cài openpyxl hoặc xlsxwriter.")
    with pd.ExcelWriter(buffer, engine=excel_engine) as writer:
        frame.to_excel(writer, sheet_name="AuditLog", index=False)
    return buffer.getvalue()


def _audit_export_pdf(title: str, logs: list[dict[str, Any]]) -> bytes:
    if SimpleDocTemplate is None:
        raise RuntimeError("Thư viện reportlab chưa sẵn sàng để xuất PDF.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.1 * cm,
        rightMargin=1.1 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = [Paragraph(html.escape(title), styles["Title"]), Spacer(1, 0.35 * cm)]

    if not logs:
        story.append(Paragraph("Không có dữ liệu audit log.", styles["BodyText"]))
    else:
        rows = [["Thời gian", "User", "Loại", "Mức", "IP", "Chi tiết"]]
        for log in logs:
            details = log.get("details") or {}
            if isinstance(details, dict):
                detail_text = json.dumps(details, ensure_ascii=False)
            else:
                detail_text = str(details)
            rows.append(
                [
                    str(log.get("created_at") or ""),
                    str(log.get("user_email") or "Hệ thống"),
                    str(log.get("event") or ""),
                    str(log.get("severity") or "Info"),
                    str(log.get("ip_address") or details.get("ip") or ""),
                    detail_text[:180],
                ]
            )
        table = Table(rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buffer.getvalue()


def _render_group_section(store: ChatStore) -> None:
    search = st.text_input("Tìm nhóm quyền", placeholder="Ví dụ: Finance")
    groups = store.list_permission_groups(search or None)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Tổng nhóm quyền", len(groups))
    with col_b:
        st.metric("Nhóm hệ thống", sum(1 for group in groups if group.get("is_system")))
    with col_c:
        st.metric("Tổng thành viên", sum(int(group.get("member_count") or 0) for group in groups))

    st.markdown("##### Thêm / sửa nhóm quyền")
    selected_group_name = st.selectbox("Chọn nhóm để sửa", ["(Tạo mới)"] + [group["name"] for group in groups], key="rbac_group_select")
    selected_group = next((group for group in groups if group["name"] == selected_group_name), None)

    with st.form("group_editor", clear_on_submit=False):
        name = st.text_input("Tên nhóm", value=selected_group["name"] if selected_group else "")
        description = st.text_area("Mô tả", value=selected_group["description"] if selected_group else "", height=90)
        max_clearance = st.slider(
            "Cấp độ bảo mật tối đa",
            min_value=1,
            max_value=5,
            value=int(selected_group.get("max_clearance_level") or 1) if selected_group else 1,
        )
        document_scope = st.text_input(
            "Phạm vi tài liệu (JSON)",
            value=json.dumps(selected_group.get("document_scope") or {}, ensure_ascii=False) if selected_group else "{}",
        )
        submitted = st.form_submit_button("Lưu nhóm quyền", use_container_width=True)
        if submitted:
            scope_payload = json.loads(document_scope or "{}")
            if selected_group:
                store.update_permission_group(selected_group["id"], name, description, max_clearance, scope_payload)
                st.success("Đã cập nhật nhóm quyền.")
            else:
                store.create_permission_group(name, description, max_clearance)
                st.success("Đã tạo nhóm quyền.")
            st.rerun()

    if selected_group:
        st.markdown("##### Ma trận phân quyền nhóm × phòng ban × mức bảo mật")
        matrix_rows = store.list_group_department_permissions(selected_group["id"])
        matrix_df = pd.DataFrame(matrix_rows)
        if matrix_df.empty:
            st.info("Nhóm này chưa có cấu hình ma trận.")
        else:
            st.dataframe(matrix_df, use_container_width=True, hide_index=True)

        with st.form("matrix_editor", clear_on_submit=False):
            department = st.selectbox("Phòng ban", DEPARTMENT_OPTIONS, key="matrix_department")
            max_sensitivity = st.selectbox("Mức bảo mật tối đa", ["public", "internal", "confidential", "restricted"], key="matrix_sensitivity")
            can_view_all = st.checkbox("Có thể xem toàn bộ tài liệu", value=False)
            if st.form_submit_button("Cập nhật ma trận", use_container_width=True):
                store.upsert_group_department_permission(selected_group["id"], department, max_sensitivity, can_view_all)
                st.success("Đã cập nhật ma trận phân quyền.")
                st.rerun()

        try:
            if st.button("Xóa nhóm quyền", type="secondary", use_container_width=True, disabled=bool(selected_group.get("is_system"))):
                store.delete_permission_group(selected_group["id"])
                st.success("Đã xóa nhóm quyền.")
                st.rerun()
        except ValueError as exc:
            st.error(str(exc))

        member_users = store.list_users(query=None)
        member_map = {group_user["id"]: group_user for group_user in member_users}
        current_members = [user for user in member_users if selected_group["name"] in (user.get("groups") or [])]
        st.markdown("##### Thành viên nhóm")
        if current_members:
            st.dataframe(pd.DataFrame(current_members), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có thành viên trong nhóm này.")

        user_candidates = store.list_users(query=None)
        user_label_map = {f"{user.get('full_name') or user.get('username')} ({user['email']})": user for user in user_candidates}
        with st.form("group_membership_editor", clear_on_submit=False):
            chosen_label = st.selectbox("Chọn user", list(user_label_map.keys()))
            action = st.radio("Hành động", ["Gán vào nhóm", "Gỡ khỏi nhóm"], horizontal=True)
            if st.form_submit_button("Thực hiện", use_container_width=True):
                chosen_user = user_label_map[chosen_label]
                if action == "Gán vào nhóm":
                    store.assign_user_to_group(chosen_user["id"], selected_group["id"])
                    st.success("Đã gán user vào nhóm.")
                else:
                    store.remove_user_from_group(chosen_user["id"], selected_group["id"])
                    st.success("Đã gỡ user khỏi nhóm.")
                st.rerun()


def _render_user_section(store: ChatStore) -> None:
    col1, col2, col3, col4 = st.columns(4)
    user_query = col1.text_input("Tìm user", placeholder="Tên, username hoặc email")
    dept_filter = col2.selectbox("Phòng ban", ["", *DEPARTMENT_OPTIONS], format_func=lambda value: "Tất cả" if value == "" else value)
    role_filter = col3.selectbox("Vai trò", ["", *ROLE_OPTIONS], format_func=lambda value: "Tất cả" if value == "" else value)
    active_filter_label = col4.selectbox("Trạng thái", ["Tất cả", "Đang hoạt động", "Vô hiệu hóa"])
    active_filter = None if active_filter_label == "Tất cả" else active_filter_label == "Đang hoạt động"

    users = store.list_users(
        query=user_query or None,
        department_id=None,
        role=role_filter or None,
        active=active_filter,
    )
    if dept_filter:
        users = [user for user in users if (user.get("department") or "") == dept_filter]

    st.markdown("##### Danh sách người dùng")
    st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

    departments = store.list_departments()
    department_map = {dept["name"]: dept["id"] for dept in departments}

    st.markdown("##### Thêm mới người dùng")
    with st.form("user_create_form", clear_on_submit=True):
        full_name = st.text_input("Họ và tên")
        username = st.text_input("Username")
        email = st.text_input("Email")
        temp_password = st.text_input("Mật khẩu tạm thời", type="password")
        role = st.selectbox("Vai trò", ROLE_OPTIONS)
        department_name = st.selectbox("Phòng ban", list(department_map.keys()))
        clearance_level = st.slider("Clearance level", 1, 5, 1)
        if st.form_submit_button("Tạo người dùng", use_container_width=True):
            user_id = store.create_user(
                full_name=full_name,
                username=username,
                email=email,
                temporary_password=temp_password,
                role=role,
                department_id=department_map.get(department_name),
                clearance_level=clearance_level,
            )
            st.success(f"Đã tạo người dùng {user_id}")
            st.rerun()

    st.markdown("##### Chỉnh sửa / vô hiệu hóa / reset mật khẩu")
    user_lookup = {f"{user.get('full_name') or user.get('username')} ({user['email']})": user for user in users}
    if user_lookup:
        selected_label = st.selectbox("Chọn user", list(user_lookup.keys()), key="selected_user_admin")
        selected_user = user_lookup[selected_label]
        with st.form("user_update_form", clear_on_submit=False):
            full_name = st.text_input("Họ và tên", value=selected_user.get("full_name") or "")
            email = st.text_input("Email", value=selected_user.get("email") or "")
            role = st.selectbox("Vai trò", ROLE_OPTIONS, index=ROLE_OPTIONS.index(selected_user.get("role") or "Employee") if (selected_user.get("role") or "Employee") in ROLE_OPTIONS else 0)
            department_name = st.selectbox("Phòng ban", list(department_map.keys()), index=list(department_map.keys()).index(selected_user.get("department") or "general") if (selected_user.get("department") or "general") in department_map else 0)
            clearance_level = st.slider("Clearance level", 1, 5, int(selected_user.get("clearance_level") or 1))
            col_submit1, col_submit2, col_submit3 = st.columns(3)
            update_clicked = col_submit1.form_submit_button("Lưu thay đổi", use_container_width=True)
            deactivate_clicked = col_submit2.form_submit_button("Vô hiệu hóa", use_container_width=True)
            reset_clicked = col_submit3.form_submit_button("Reset mật khẩu", use_container_width=True)

            if update_clicked:
                store.update_user(
                    selected_user["id"],
                    full_name=full_name,
                    email=email,
                    role=role,
                    department_id=department_map.get(department_name),
                    clearance_level=clearance_level,
                )
                st.success("Đã cập nhật user.")
                st.rerun()
            if deactivate_clicked:
                store.set_user_active(selected_user["id"], False)
                st.success("Đã vô hiệu hóa user.")
                st.rerun()
            if reset_clicked:
                temp_password = store.reset_user_password(selected_user["id"])
                st.warning(f"Mật khẩu tạm thời: {temp_password}")
                st.rerun()

        if st.button("Kích hoạt tài khoản", use_container_width=True):
            store.set_user_active(selected_user["id"], True)
            st.success("Đã kích hoạt user.")
            st.rerun()
        if st.button("Force Logout", use_container_width=True):
            store.force_logout_user(selected_user["id"])
            st.success("Đã invalidate session hiện tại.")
            st.rerun()

        st.markdown("##### Gán / gỡ nhóm quyền")
        all_groups = store.list_permission_groups()
        group_lookup = {group["name"]: group for group in all_groups}
        with st.form("user_group_form", clear_on_submit=False):
            group_name = st.selectbox("Nhóm quyền", list(group_lookup.keys()))
            action = st.radio("Hành động", ["Gán", "Gỡ"], horizontal=True)
            if st.form_submit_button("Thực hiện", use_container_width=True):
                chosen_group = group_lookup[group_name]
                if action == "Gán":
                    store.assign_user_to_group(selected_user["id"], chosen_group["id"])
                    st.success("Đã gán nhóm quyền.")
                else:
                    store.remove_user_from_group(selected_user["id"], chosen_group["id"])
                    st.success("Đã gỡ nhóm quyền.")
                st.rerun()

        st.markdown("##### Preview hiệu lực phân quyền")
        docs = []
        try:
            from src.rag.vector_store import VectorStoreManager
            docs = VectorStoreManager().list_documents()
        except Exception:
            docs = []
        if docs:
            doc_lookup = {doc["file_name"]: doc for doc in docs}
            with st.form("access_preview_form", clear_on_submit=False):
                doc_name = st.selectbox("Tài liệu", list(doc_lookup.keys()))
                if st.form_submit_button("Xem preview", use_container_width=True):
                    preview = store.preview_user_access(selected_user["id"], doc_lookup[doc_name]["id"])
                    st.write(preview)


def _render_audit_section(store: ChatStore) -> None:
    st.markdown("##### Audit log chỉ đọc")
    col1, col2, col3, col4 = st.columns(4)
    user_query = col1.text_input("User / email", placeholder="tìm theo email")
    event_query = col2.text_input("Loại thao tác", placeholder="login, upload, query")
    ip_query = col3.text_input("Địa chỉ IP", placeholder="127.0.0.1")
    severity_filter = col4.selectbox("Mức độ", ["Tất cả", *SEVERITY_OPTIONS])

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input("Từ ngày", value=dt.date.today() - dt.timedelta(days=7), key="audit_start_date")
    with date_col2:
        end_date = st.date_input("Đến ngày", value=dt.date.today(), key="audit_end_date")

    logs, total = store.get_audit_logs(
        limit=200,
        offset=0,
        event_type=event_query or None,
        email_query=user_query or None,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    enriched_logs: list[dict[str, Any]] = []
    for log in logs:
        details = log.get("details") or {}
        severity = _severity_for_event(log.get("event", ""))
        if severity_filter != "Tất cả" and severity != severity_filter:
            continue
        ip_address = ""
        if isinstance(details, dict):
            ip_address = str(details.get("ip") or details.get("client_ip") or "")
        if ip_query and ip_query not in ip_address:
            continue
        enriched_logs.append({**log, "severity": severity, "ip_address": ip_address})

    audit_df = pd.DataFrame(enriched_logs)
    st.caption(f"Tổng log khớp lọc: {len(enriched_logs)} / {total}")

    export_col1, export_col2 = st.columns(2)
    with export_col1:
        try:
            excel_bytes = _audit_export_excel(enriched_logs)
            st.download_button(
                "Xuất Excel",
                data=excel_bytes,
                file_name="audit_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Không xuất được Excel: {exc}")
    with export_col2:
        try:
            pdf_bytes = _audit_export_pdf("Audit Log", enriched_logs)
            st.download_button(
                "Xuất PDF",
                data=pdf_bytes,
                file_name="audit_log.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Không xuất được PDF: {exc}")

    if audit_df.empty:
        st.info("Không có audit log khớp bộ lọc.")
        return

    st.dataframe(
        audit_df[["created_at", "user_email", "event", "severity", "ip_address", "details"]],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("##### Chi tiết log entry")
    selected_index = st.selectbox("Chọn log", list(range(len(enriched_logs))), format_func=lambda idx: f"{enriched_logs[idx].get('created_at')} - {enriched_logs[idx].get('event')}")
    selected_log = enriched_logs[selected_index]
    st.json(selected_log)


def render_rbac_admin_page(store: ChatStore | None = None) -> None:
    store = store or ChatStore(db_url=POSTGRES_CONNECTION_STRING)
    st.markdown('<h2 style="font-weight: 700; font-size: 24px; color: #0f172a; margin-top: 10px;">⚙️ Quản trị RBAC</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: #64748b; font-size: 13px; margin-top: -12px;">Quản lý nhóm quyền, người dùng và nhật ký audit chỉ đọc.</p>', unsafe_allow_html=True)
    st.markdown("---")

    tabs = st.tabs(["Nhóm quyền", "Người dùng", "Audit Log"])
    with tabs[0]:
        _render_group_section(store)
    with tabs[1]:
        _render_user_section(store)
    with tabs[2]:
        _render_audit_section(store)
