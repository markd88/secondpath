from __future__ import annotations

import sqlite3

from secondpath import FallbackLayer, protect
from secondpath.detectors import ExceptionType
from secondpath.sinks import MessageQueueSink, SqliteSink


class FailingSink:
    def emit(self, incident) -> None:
        raise RuntimeError("sink unavailable")


class CollectingSink:
    def __init__(self) -> None:
        self.incidents = []

    def emit(self, incident) -> None:
        self.incidents.append(incident)


def test_sink_failure_does_not_break_main_execution_path() -> None:
    def primary(url: str) -> dict:
        raise TimeoutError("timeout")

    def fallback(url: str) -> dict:
        return {"headline": "fallback"}

    collecting_sink = CollectingSink()
    plan = protect(
        primary=primary,
        detect=[ExceptionType(TimeoutError, "timeout")],
        fallback_chain=[FallbackLayer.rule_based("template", fallback)],
        sinks=[FailingSink(), collecting_sink],
    )

    result = plan.run(url="https://merchant.example")

    assert result.status.value == "degraded"
    assert result.output == {"headline": "fallback"}
    assert len(collecting_sink.incidents) == 1


def test_sqlite_sink_persists_incident(tmp_path) -> None:
    def primary(url: str) -> dict:
        raise TimeoutError("timeout")

    def fallback(url: str) -> dict:
        return {"headline": "fallback"}

    db_path = tmp_path / "incidents.db"
    plan = protect(
        primary=primary,
        detect=[ExceptionType(TimeoutError, "timeout")],
        fallback_chain=[FallbackLayer.rule_based("template", fallback)],
        sinks=[SqliteSink(str(db_path))],
    )

    result = plan.run(url="https://merchant.example")

    assert result.incident_id is not None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT incident_id, failure_type, final_status FROM incidents WHERE incident_id = ?",
            (result.incident_id,),
        ).fetchone()

    assert row == (result.incident_id, "timeout", "degraded")


def test_message_queue_sink_publishes_incident_payload() -> None:
    published = []

    def primary(url: str) -> dict:
        raise TimeoutError("timeout")

    def fallback(url: str) -> dict:
        return {"headline": "fallback"}

    def publisher(payload: dict) -> None:
        published.append(payload)

    plan = protect(
        primary=primary,
        detect=[ExceptionType(TimeoutError, "timeout")],
        fallback_chain=[FallbackLayer.rule_based("template", fallback)],
        sinks=[MessageQueueSink(publisher=publisher, topic="human.review")],
    )

    result = plan.run(url="https://merchant.example")

    assert result.incident_id is not None
    assert len(published) == 1
    assert published[0]["topic"] == "human.review"
    assert published[0]["incident"]["incident_id"] == result.incident_id
    assert published[0]["incident"]["failure_type"] == "timeout"
