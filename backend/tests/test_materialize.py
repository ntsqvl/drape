"""Result URLs are presigned S3 links that die after ~2 hours; the cache
keeps payloads for weeks. A cached URL must never be re-fetched when the
render already exists on disk, and a dead URL with no local file must
trigger a forced re-render instead of surfacing a 403."""

import pytest
import requests

from drape import config
from drape.api import cloth_vto
from drape.api.youcam_client import FileHandle, TaskResult


def test_materialize_prefers_existing_local_file(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RENDERS_DIR", tmp_path)
    (tmp_path / "abc123.jpg").write_bytes(b"render bytes")

    def explode(*a, **k):
        raise AssertionError("network touched despite local file")

    monkeypatch.setattr(cloth_vto.requests, "get", explode)
    url = "https://yce-us.s3.amazonaws.com/ttl30/x/abc123.jpg?X-Amz-Expires=7200&sig=expired"
    assert cloth_vto._materialize(url) == tmp_path / "abc123.jpg"


class ExpiredThenFreshClient:
    """First run_task returns a dead URL; the forced retry returns a live one."""

    mock = False

    def __init__(self, fresh_file):
        self.fresh_file = fresh_file
        self.calls = []

    def upload(self, feature, path):
        return FileHandle(feature, "id", "digest")

    def run_task(self, feature, params, *, src=None, cache_extra="", force=False):
        self.calls.append(force)
        url = (
            self.fresh_file.as_uri()
            if force
            else "https://yce-us.s3.amazonaws.com/ttl30/x/gone.jpg?expired=1"
        )
        return TaskResult(feature, "t", {"results": {"url": url}})


def test_expired_cached_url_triggers_forced_rerender(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RENDERS_DIR", tmp_path)  # gone.jpg is NOT on disk

    def forbidden(url, timeout=0):
        resp = requests.Response()
        resp.status_code = 403
        raise requests.HTTPError("403 Forbidden", response=resp)

    monkeypatch.setattr(cloth_vto.requests, "get", forbidden)
    fresh = tmp_path / "fresh.jpg"
    fresh.write_bytes(b"new render")
    client = ExpiredThenFreshClient(fresh)

    out = cloth_vto.try_on(client, FileHandle("cloth-v3", "id", "d"), tmp_path / "drape.jpg")
    assert out == fresh
    assert client.calls == [False, True]  # cache attempt, then forced re-render
