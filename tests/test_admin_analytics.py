"""Tests for the AI dashboard and usage report analytics helpers."""

from __future__ import annotations

import datetime as dt

import pytest

import src.admin_analytics as analytics


@pytest.fixture
def sample_logs() -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)
    return [
        {
            "event": "question_allowed",
            "created_at": now - dt.timedelta(hours=2),
            "user_email": "alice@example.com",
            "department": "hr",
            "details": {
                "question_text": "Quy định nghỉ phép là gì?",
                "question_preview": "Quy định nghỉ phép là gì?",
                "sources_count": 2,
                "sources": ["hr_policy.pdf", "leave_handbook.pdf"],
                "latency_ms": 420.0,
            },
        },
        {
            "event": "question_allowed",
            "created_at": now - dt.timedelta(hours=1),
            "user_email": "bob@example.com",
            "department": "finance",
            "details": {
                "question_text": "Hạn mức khách sạn là bao nhiêu?",
                "question_preview": "Hạn mức khách sạn là bao nhiêu?",
                "sources_count": 1,
                "sources": ["travel_policy.pdf"],
                "latency_ms": 300.0,
            },
        },
        {
            "event": "question_allowed",
            "created_at": now - dt.timedelta(minutes=30),
            "user_email": "alice@example.com",
            "department": "hr",
            "details": {
                "question_text": "Quy định nghỉ phép là gì?",
                "question_preview": "Quy định nghỉ phép là gì?",
                "sources_count": 0,
                "sources": [],
                "latency_ms": 180.0,
            },
        },
    ]


def test_build_activity_snapshot_aggregates_key_metrics(sample_logs):
    snapshot = analytics.build_activity_snapshot(
        sample_logs,
        selected_department="all",
        indexed_documents=12,
        include_user_breakdown=True,
    )

    assert snapshot["summary"]["total_queries"] == 3
    assert snapshot["summary"]["successful_queries"] == 2
    assert snapshot["summary"]["no_source_queries"] == 1
    assert snapshot["summary"]["indexed_documents"] == 12
    assert not snapshot["hourly_df"].empty
    assert list(snapshot["question_df"]["question"]) == [
        "Quy định nghỉ phép là gì?",
        "Hạn mức khách sạn là bao nhiêu?",
    ]
    assert list(snapshot["document_df"]["document"]) == [
        "hr_policy.pdf",
        "leave_handbook.pdf",
        "travel_policy.pdf",
    ]
    assert not snapshot["latency_df"].empty
    assert not snapshot["user_df"].empty


def test_build_resource_status_flags_stale_backup(monkeypatch, tmp_path):
    monkeypatch.setattr(analytics, "get_system_ram_usage_percent", lambda: 74.0)
    monkeypatch.setattr(analytics, "get_vram_usage_percent", lambda: 88.0)
    stale_backup = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)
    monkeypatch.setattr(analytics, "get_last_backup_timestamp", lambda _base_dir: stale_backup)

    status = analytics.build_resource_status(
        queue_size=31,
        queue_max=10,
        base_dir=tmp_path,
    )

    assert status["ram_usage"] == 74.0
    assert status["vram_usage"] == 88.0
    assert status["backup_warning"] == "Chưa backup trong 25.0 giờ"
    assert any("VRAM" in warning for warning in status["warnings"])
    assert any("Queue" in warning for warning in status["warnings"])
    assert any("backup" in warning.lower() for warning in status["warnings"])
