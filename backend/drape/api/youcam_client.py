"""Shared YouCam API client: file upload, task submit, poll, cache, mock.

Endpoint shapes verified against docs.perfectcorp.com (July 2026):
  POST /s2s/v2.0/file/{feature}            declare file -> file_id + presigned PUT
  PUT  <presigned url>                     upload the actual bytes
  POST /s2s/v2.0/task/{feature}            create task -> task_id
  GET  /s2s/v2.0/task/{feature}/{task_id}  poll -> data.task_status running|success|error
  GET  /s2s/v1.0/client/credit             remaining units
  GET  /s2s/v2.0/credit/feature-cost       per-feature unit costs

Hard-won constraints this module enforces so callers can't get them wrong:
  * Task failure comes back as HTTP 200 with task_status "error" -- we inspect
    the body, never the HTTP status alone.
  * file_id is scoped to the feature it was uploaded for; upload() takes the
    feature name and the returned FileHandle refuses to be used elsewhere.
  * Declaring a file does NOT upload it; the PUT to the presigned URL is
    mandatory or later task calls fail with unknown_internal_error / 404.
  * Polling within the task retention period is mandatory: an unpolled task
    times out and its units are still consumed on success.
  * skin-tone-analysis accepts jpg/jpeg only.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from drape import config

# Features we use. The file-API scope name matches the task name.
SKIN_TONE = "skin-tone-analysis"
SKIN_ANALYSIS = "skin-analysis"
CLOTH = "cloth-v3"

JPEG_ONLY_FEATURES = {SKIN_TONE}

POLL_INTERVAL_S = 2.0
POLL_TIMEOUT_S = 240.0


class YouCamError(Exception):
    def __init__(self, message: str, *, error_code: str | None = None, payload: dict | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.payload = payload or {}


def task_error(data: dict, body: dict | None = None) -> YouCamError:
    """Build a YouCamError from a failed task's `data` object.

    The live API is loose about the error shape: `error` may be a dict with
    message/error_code, a bare code string like "error_src_face_too_small",
    or null with the code in a sibling field. Handle all of them -- an error
    handler that crashes hides the actual failure from the user.
    """
    err = data.get("error")
    code = data.get("error_code")
    if isinstance(err, dict):
        message = err.get("message") or err.get("error") or "task failed"
        code = code or err.get("error_code") or err.get("code")
    else:
        message = str(err) if err else "task failed"
        if code is None and isinstance(err, str) and err.startswith("error_"):
            code = err
    return YouCamError(str(message), error_code=code, payload=body or data)


@dataclass(frozen=True)
class FileHandle:
    feature: str
    file_id: str
    digest: str = ""  # content hash; cache identity that survives re-uploads


@dataclass
class TaskResult:
    feature: str
    task_id: str
    payload: dict  # the full "data" object of the final poll response

    @property
    def results(self) -> dict:
        return self.payload.get("results") or {}


class YouCamClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        cache_dir: Path | None = None,
        mock: bool | None = None,
    ):
        self.api_key = api_key if api_key is not None else config.API_KEY
        self.base_url = (base_url or config.API_BASE).rstrip("/")
        self.cache_dir = Path(cache_dir) if cache_dir else config.CACHE_DIR
        self.mock = config.MOCK if mock is None else mock
        self.session = requests.Session()
        if not self.mock and not self.api_key:
            raise YouCamError(
                "YOUCAM_API_KEY is not set. Set it in .env, or set YOUCAM_MOCK=1 to run offline."
            )

    # ---------------------------------------------------------------- http

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _check_body(self, resp: requests.Response) -> dict:
        """Raise on HTTP-level and body-level errors; return parsed JSON."""
        try:
            body = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise YouCamError(f"Non-JSON response (HTTP {resp.status_code})")
        # The API signals errors both via HTTP status and via body fields;
        # trust the body first (gotcha #1).
        if body.get("error") or (isinstance(body.get("status"), int) and body["status"] >= 400):
            raise YouCamError(
                str(body.get("error") or f"API error (status {body.get('status')})"),
                error_code=body.get("error_code"),
                payload=body,
            )
        resp.raise_for_status()
        return body

    # --------------------------------------------------------------- cache

    def _cache_key(self, *parts: str) -> Path:
        digest = hashlib.sha256("||".join(parts).encode()).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def _cache_get(self, key: Path) -> dict | None:
        if key.exists():
            return json.loads(key.read_text())
        return None

    def _cache_put(self, key: Path, value: dict) -> None:
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps(value, indent=2))

    # -------------------------------------------------------------- upload

    def upload(self, feature: str, path: str | Path) -> FileHandle:
        """Two-stage upload: declare -> PUT bytes -> file_id (scoped to feature)."""
        path = Path(path)
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if feature in JPEG_ONLY_FEATURES and content_type not in ("image/jpeg", "image/jpg"):
            raise YouCamError(
                f"{feature} accepts jpg/jpeg only; got {content_type}. Convert the image first."
            )
        digest = hashlib.sha256(data).hexdigest()[:16]
        if self.mock:
            # Embed the source path so the mock engine can read the real pixels.
            return FileHandle(feature, f"mock:{digest}:{path.resolve()}", digest)

        declare = self._check_body(
            self.session.post(
                f"{self.base_url}/s2s/v2.0/file/{feature}",
                headers=self._headers(),
                json={
                    "files": [
                        {
                            "content_type": content_type,
                            "file_name": path.name,
                            "file_size": len(data),
                        }
                    ]
                },
                timeout=30,
            )
        )
        entry = declare["data"]["files"][0]
        put = entry["requests"][0]
        # Stage 2 is mandatory (gotcha #2): without this PUT the file_id is a dud.
        up = self.session.request(
            put.get("method", "PUT"), put["url"], data=data, headers=put.get("headers") or {}, timeout=120
        )
        up.raise_for_status()
        return FileHandle(feature, entry["file_id"], digest)

    # --------------------------------------------------------------- tasks

    def run_task(
        self,
        feature: str,
        params: dict,
        *,
        src: FileHandle | None = None,
        cache_extra: str = "",
        force: bool = False,
    ) -> TaskResult:
        """Create a task, poll to completion, return the final payload.

        `src` (if given) must be a FileHandle uploaded for this same feature
        (gotcha #3). Results are disk-cached; a cache hit costs 0 units.
        `force=True` bypasses the cache read (still refreshes the entry) --
        used when a cached result URL has expired (presigned links last ~2h).
        """
        if src is not None:
            if src.feature != feature:
                raise YouCamError(
                    f"file_id is scoped per feature: got a {src.feature} file for a {feature} task. "
                    "Re-upload the image for this feature."
                )
            params = {**params, "src_file_id": src.file_id}

        # Cache identity must come from CONTENT, never from *_file_id values:
        # the live API mints a fresh file_id on every upload, so keying on
        # them means retries of the same photo re-bill instead of hitting
        # cache. ref-image identity travels in cache_extra (a stable path).
        key_params = {k: v for k, v in params.items() if not k.endswith("_file_id")}
        key = self._cache_key(
            feature,
            json.dumps(key_params, sort_keys=True),
            src.digest if src is not None else "",
            cache_extra,
        )
        cached = None if force else self._cache_get(key)
        if cached is not None:
            return TaskResult(feature, cached.get("task_id", "cached"), cached["payload"])

        if self.mock:
            payload = self._mock_task(feature, params)
            self._cache_put(key, {"task_id": "mock", "payload": payload})
            return TaskResult(feature, "mock", payload)

        created = self._check_body(
            self.session.post(
                f"{self.base_url}/s2s/v2.0/task/{feature}",
                headers=self._headers(),
                json=params,
                timeout=30,
            )
        )
        task_id = created["data"]["task_id"]
        payload = self._poll(feature, task_id)
        self._cache_put(key, {"task_id": task_id, "payload": payload})
        return TaskResult(feature, task_id, payload)

    def _poll(self, feature: str, task_id: str) -> dict:
        deadline = time.monotonic() + POLL_TIMEOUT_S
        while True:
            body = self._check_body(
                self.session.get(
                    f"{self.base_url}/s2s/v2.0/task/{feature}/{task_id}",
                    headers=self._headers(),
                    timeout=30,
                )
            )
            data = body.get("data") or {}
            status = data.get("task_status")
            if status == "success":
                return data
            if status == "error":
                # HTTP was 200; the failure lives in the body (gotcha #1).
                raise task_error(data, body)
            if time.monotonic() > deadline:
                raise YouCamError(f"{feature} task {task_id} still running after {POLL_TIMEOUT_S}s")
            time.sleep(POLL_INTERVAL_S)

    # -------------------------------------------------------------- credit

    def credit(self) -> dict:
        if self.mock:
            return {"mock": True, "credits": 1000}
        return self._check_body(
            self.session.get(f"{self.base_url}/s2s/v1.0/client/credit", headers=self._headers(), timeout=30)
        )

    def remaining_units(self) -> float:
        """Sum of all unexpired unit grants on the account."""
        if self.mock:
            return 1000.0
        body = self.credit()
        return float(sum(r.get("amount_dec", r.get("amount", 0)) for r in body.get("results", [])))

    def feature_cost(self) -> dict:
        """Full SKU catalog; the endpoint paginates via `starting_token`."""
        if self.mock:
            return {"mock": True, "skus": []}
        skus: list[dict] = []
        token: str | None = None
        for _ in range(20):
            url = f"{self.base_url}/s2s/v2.0/credit/feature-cost"
            if token:
                url += f"?starting_token={token}"
            body = self._check_body(self.session.get(url, headers=self._headers(), timeout=30))
            result = body.get("result") or {}
            skus += result.get("skus", [])
            token = result.get("next_token")
            if not token:
                break
        return {"skus": skus}

    # ---------------------------------------------------------------- mock

    def _mock_task(self, feature: str, params: dict) -> dict:
        from drape.api import mock_engine

        return mock_engine.run(feature, params)
