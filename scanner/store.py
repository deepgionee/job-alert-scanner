"""Tracks seen job IDs in data/seen_jobs.json — persists between runs."""
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent.parent / "data" / "seen_jobs.json"

class JobStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = json.loads(self.path.read_text()) if self.path.exists()                      else {"seen_ids": {}, "last_run": None}

    def _save(self):
        self.path.write_text(json.dumps(self._data, indent=2))

    def find_new(self, jobs):
        seen = self._data["seen_ids"]
        new  = [j for j in jobs if j["id"] not in seen]
        for j in new:
            seen[j["id"]] = {"title": j["title"], "company": j["company"],
                             "first_seen": datetime.now(timezone.utc).isoformat()}
        self._data["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save()
        return new

    @property
    def total_seen(self): return len(self._data["seen_ids"])
    @property
    def last_run(self):   return self._data.get("last_run")
