"""Simple incident sinks."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import request

from secondpath.types import Incident


@dataclass
class StdoutSink:
    def emit(self, incident: Incident) -> None:
        print(json.dumps(asdict(incident), default=str, sort_keys=True))


@dataclass
class WebhookSink:
    url: str
    timeout_seconds: float = 5.0

    def emit(self, incident: Incident) -> None:
        payload = json.dumps(asdict(incident), default=str).encode("utf-8")
        req = request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds):
            return None


@dataclass
class SlackSink:
    webhook_url: str
    timeout_seconds: float = 5.0

    def emit(self, incident: Incident) -> None:
        body = {
            "text": (
                f"[{incident.plan_name}] {incident.summary} "
                f"(failure_type={incident.failure_type}, status={incident.final_status.value})"
            )
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds):
            return None


@dataclass
class MessageQueueSink:
    publisher: Callable[[dict[str, Any]], None]
    topic: str = "secondpath.incidents"

    def emit(self, incident: Incident) -> None:
        incident_payload = asdict(incident)
        incident_payload["final_status"] = incident.final_status.value
        payload = {
            "topic": self.topic,
            "incident": incident_payload,
        }
        self.publisher(payload)


@dataclass
class SqliteSink:
    path: str

    def emit(self, incident: Incident) -> None:
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    failed_stage TEXT,
                    triggered_by TEXT NOT NULL,
                    fallback_attempted TEXT NOT NULL,
                    final_status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO incidents (
                    incident_id,
                    execution_id,
                    plan_name,
                    failure_type,
                    failed_stage,
                    triggered_by,
                    fallback_attempted,
                    final_status,
                    summary,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident.incident_id,
                    incident.execution_id,
                    incident.plan_name,
                    incident.failure_type,
                    incident.failed_stage,
                    incident.triggered_by,
                    json.dumps(incident.fallback_attempted),
                    incident.final_status.value,
                    incident.summary,
                    json.dumps(incident.metadata, default=str),
                ),
            )
