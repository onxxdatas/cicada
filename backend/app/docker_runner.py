"""
Launches k6 via the HOST docker daemon (Docker-outside-of-Docker), tails the
NDJSON metrics file it writes, aggregates it into 1-second buckets, and
streams those buckets to any browser subscribed to the run over a WebSocket.

This module intentionally uses only synchronous docker-py calls, wrapped in
asyncio.to_thread — docker-py has no native async API.
"""

import asyncio
import json
import math
import os
import time
from datetime import datetime, timezone

import docker

from app.config import settings
from app.database import SessionLocal
from app.k6_script_generator import generate_k6_script
from app.models import Run, Test
from app.ws_manager import ws_manager

POLL_INTERVAL_SECONDS = 1.0
DB_FLUSH_EVERY = 3  # persist timeline to Postgres every N polls


def _now():
    return datetime.now(timezone.utc)


def _bucket_key(iso_time: str) -> int:
    """Floor an ISO-8601 timestamp to the second, as a unix epoch int."""
    # k6's NDJSON timestamps look like '2026-07-04T10:11:12.345678901Z'
    cleaned = iso_time.split(".")[0].replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


class _Bucket:
    __slots__ = ("requests", "durations", "failed", "vus")

    def __init__(self):
        self.requests = 0
        self.durations: list[float] = []
        self.failed = 0
        self.vus = 0

    def to_point(self, second: int) -> dict:
        avg_ms = sum(self.durations) / len(self.durations) if self.durations else 0.0
        sorted_d = sorted(self.durations)
        p95_ms = 0.0
        if sorted_d:
            idx = min(len(sorted_d) - 1, math.ceil(0.95 * len(sorted_d)) - 1)
            p95_ms = sorted_d[idx]
        error_rate = (self.failed / self.requests) if self.requests else 0.0
        return {
            "t": second,
            "vus": self.vus,
            "rps": self.requests,
            "avg_ms": round(avg_ms, 1),
            "p95_ms": round(p95_ms, 1),
            "error_rate": round(error_rate, 4),
        }


async def _tail_and_broadcast(run_id: str, results_path: str, stop_event: asyncio.Event) -> list[dict]:
    """Poll the NDJSON results file as it grows, aggregate into per-second
    buckets, broadcast each completed bucket, and return the full timeline."""
    timeline: list[dict] = []
    buckets: dict[int, _Bucket] = {}
    last_completed_second: int | None = None
    offset = 0
    polls_since_flush = 0

    while True:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

        if os.path.exists(results_path):
            with open(results_path, "r") as f:
                f.seek(offset)
                new_lines = f.readlines()
                offset = f.tell()

            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    point = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if point.get("type") != "Point":
                    continue

                metric = point.get("metric")
                data = point.get("data", {})
                value = data.get("value")
                iso_time = data.get("time")
                if value is None or not iso_time:
                    continue

                second = _bucket_key(iso_time)
                bucket = buckets.setdefault(second, _Bucket())

                if metric == "http_reqs":
                    bucket.requests += 1
                elif metric == "http_req_duration":
                    bucket.durations.append(value)
                elif metric == "http_req_failed":
                    bucket.failed += int(value)
                elif metric == "vus":
                    bucket.vus = max(bucket.vus, int(value))

        # Flush any second that is now safely in the past (data for it has
        # stopped arriving because k6 has moved on).
        ready_seconds = sorted(s for s in buckets if last_completed_second is None or s > last_completed_second)
        cutoff = int(time.time()) - 2  # give k6 a couple seconds of slack
        for second in ready_seconds:
            if second >= cutoff:
                continue
            point = buckets[second].to_point(second)
            timeline.append(point)
            await ws_manager.broadcast(run_id, {"type": "point", "point": point})
            last_completed_second = second
            del buckets[second]

        polls_since_flush += 1
        if polls_since_flush >= DB_FLUSH_EVERY and timeline:
            polls_since_flush = 0
            _persist_timeline(run_id, timeline)

        if stop_event.is_set():
            # Drain whatever is left once the container has finished.
            for second in sorted(buckets):
                point = buckets[second].to_point(second)
                timeline.append(point)
                await ws_manager.broadcast(run_id, {"type": "point", "point": point})
            break

    return timeline


def _persist_timeline(run_id: str, timeline: list[dict]) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run:
            run.timeline = timeline
            db.commit()
    finally:
        db.close()


def _read_summary(summary_path: str) -> dict | None:
    if not os.path.exists(summary_path):
        return None
    try:
        with open(summary_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


async def run_test(run_id: str, test_id: str) -> None:
    db = SessionLocal()
    try:
        test = db.get(Test, test_id)
        run = db.get(Run, run_id)
        if not test or not run:
            return

        script = generate_k6_script(test)
        script_filename = f"run_{run_id}.js"
        results_filename = f"run_{run_id}.json"
        summary_filename = f"run_{run_id}_summary.json"

        os.makedirs(settings.SCRIPTS_DIR, exist_ok=True)
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)
        with open(os.path.join(settings.SCRIPTS_DIR, script_filename), "w") as f:
            f.write(script)

        run.status = "running"
        run.started_at = _now()
        db.commit()
    finally:
        db.close()

    results_path = os.path.join(settings.RESULTS_DIR, results_filename)
    summary_path = os.path.join(settings.RESULTS_DIR, summary_filename)

    client = docker.from_env()
    container = None
    exit_code = None
    error_message = None

    try:
        container = await asyncio.to_thread(
            client.containers.run,
            settings.K6_IMAGE,
            command=[
                "run",
                "--out",
                f"json=/results/{results_filename}",
                "--summary-export",
                f"/results/{summary_filename}",
                f"/scripts/{script_filename}",
            ],
            volumes={
                settings.host_scripts_dir: {"bind": "/scripts", "mode": "ro"},
                settings.host_results_dir: {"bind": "/results", "mode": "rw"},
            },
            network=settings.COMPOSE_NETWORK,
            detach=True,
        )

        db = SessionLocal()
        try:
            run = db.get(Run, run_id)
            if run:
                run.container_id = container.id
                db.commit()
        finally:
            db.close()

        stop_event = asyncio.Event()
        tail_task = asyncio.create_task(_tail_and_broadcast(run_id, results_path, stop_event))

        wait_result = await asyncio.to_thread(container.wait)
        exit_code = wait_result.get("StatusCode", -1)

        stop_event.set()
        timeline = await tail_task

    except Exception as exc:  # docker daemon unreachable, image missing, etc.
        error_message = str(exc)
        timeline = []
    finally:
        if container is not None:
            try:
                await asyncio.to_thread(container.remove, force=True)
            except Exception:
                pass

    summary = _read_summary(summary_path)

    if error_message:
        status = "error"
    elif exit_code == 0:
        status = "passed"
    elif exit_code == 99:
        status = "failed"  # thresholds violated
    else:
        status = "error"

    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run:
            run.status = status
            run.finished_at = _now()
            run.summary = summary
            run.timeline = timeline or run.timeline
            run.error = error_message
            db.commit()
    finally:
        db.close()

    await ws_manager.broadcast(
        run_id,
        {"type": "done", "status": status, "summary": summary, "error": error_message},
    )
