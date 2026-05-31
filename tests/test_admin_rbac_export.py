from __future__ import annotations

import datetime as dt

from src.admin_rbac import _audit_export_excel


def test_audit_export_excel_accepts_timezone_aware_datetimes():
    payload = _audit_export_excel(
        [
            {
                "created_at": dt.datetime(
                    2026, 5, 31, 10, 30, tzinfo=dt.timezone.utc
                ),
                "user_email": "admin@example.com",
                "event": "user_login",
                "severity": "Info",
            }
        ]
    )

    assert payload.startswith(b"PK")
