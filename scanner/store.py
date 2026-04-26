"""
Persistent state store — keeps track of every job ID we have seen before.
Uses a simple JSON file so there are no database dependencies.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent.parent / "data" / "seen_jobs.json"


class JobStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {"seen_ids": {}, "last_run": None}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def find_new(self, jobs: list[dict]) -> list[dict]:
        seen = self._data["seen_ids"]
        new_jobs = [j for j in jobs if j["id"] not in seen]
        for j in new_jobs:
            seen[j["id"]] = {
                "title": j["title"],
                "company": j["company"],
                "first_seen": datetime.now(timezone.utc).isoformat(),
            }
        self._data["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save()
        return new_jobs

    @property
    def last_run(self) -> str | None:
        return self._data.get("last_run")

    @property
    def total_seen(self) -> int:
        return len(self._data["seen_ids"])
