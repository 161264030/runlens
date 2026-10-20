import json
import os

import pytest

from runlens.models.run import RunRecord
from runlens.storage.json_store import JsonStore, StorageError


def saved(tmp_path):
    store = JsonStore(tmp_path)
    record = RunRecord("run_" + "a" * 32, ["echo", "hello"], "/tmp", "2026-10-20", 1, 0.02)
    directory = store.create(record)
    return store, record, directory


def test_save_load_and_empty_listing(tmp_path):
    assert JsonStore(tmp_path / "absent").list_runs() == ([], [])
    store, record, directory = saved(tmp_path)
    record.state = "completed"
    store.save(record)
    assert store.load(record.run_id)["state"] == "completed"
    records, warnings = store.list_runs()
    assert len(records) == 1 and not warnings
    assert not (directory / "metadata.json.tmp").exists()


@pytest.mark.parametrize("run_id", ["../other", "/tmp/x", "run_../../x", "not-an-id"])
def test_rejects_path_traversal(tmp_path, run_id):
    with pytest.raises(ValueError, match="Invalid run ID"):
        JsonStore(tmp_path).load(run_id)


@pytest.mark.parametrize(
    "content", ["{bad", "[]", '{"schema_version":"9.9"}', '{"schema_version":"0.1"}']
)
def test_corrupt_metadata_reported(tmp_path, content):
    store, record, directory = saved(tmp_path)
    (directory / "metadata.json").write_text(content)
    with pytest.raises(StorageError):
        store.load(record.run_id)
    records, warnings = store.list_runs()
    assert not records and len(warnings) == 1


def test_invalid_argv_reported(tmp_path):
    store, record, directory = saved(tmp_path)
    data = record.to_dict()
    data["argv"] = "not a list"
    (directory / "metadata.json").write_text(json.dumps(data))
    with pytest.raises(StorageError):
        store.load(record.run_id)


@pytest.mark.parametrize(
    "field,value",
    [
        ("peak_threads", -1),
        ("sample_count", True),
        ("state", "unknown"),
        ("duration_s", float("nan")),
        ("sample_interval_s", 0),
        ("capture_notes", "invalid"),
    ],
)
def test_invalid_schema_fields(tmp_path, field, value):
    store, record, directory = saved(tmp_path)
    data = record.to_dict()
    data[field] = value
    (directory / "metadata.json").write_text(json.dumps(data))
    with pytest.raises(StorageError):
        store.load(record.run_id)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_private_permissions(tmp_path):
    store, record, directory = saved(tmp_path)
    with store.open_samples(record.run_id):
        pass
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "metadata.json").stat().st_mode & 0o777 == 0o600
    assert (directory / "resources.jsonl").stat().st_mode & 0o777 == 0o600
