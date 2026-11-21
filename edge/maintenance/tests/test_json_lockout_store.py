import json
from pathlib import Path

import pytest

from maintenance.adapters.json_lockout_store import JsonFileLockoutStore
from maintenance.ports import LockoutStoreError


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "estado" / "candados.json"


def test_missing_file_means_no_lockouts(path):
    assert JsonFileLockoutStore(path).load() == set()


def test_saved_lockouts_can_be_loaded_back(path):
    JsonFileLockoutStore(path).save({"trituradora-01", "cinta-02"})
    assert JsonFileLockoutStore(path).load() == {"trituradora-01", "cinta-02"}


def test_save_replaces_previous_content(path):
    store = JsonFileLockoutStore(path)
    store.save({"trituradora-01", "cinta-02"})
    store.save({"cinta-02"})
    assert store.load() == {"cinta-02"}


def test_save_creates_missing_directory_and_leaves_no_temp_files(path):
    JsonFileLockoutStore(path).save({"cinta-02"})
    assert [p.name for p in path.parent.iterdir()] == ["candados.json"]


def test_file_is_human_readable_and_sorted(path):
    JsonFileLockoutStore(path).save({"trituradora-01", "cinta-02"})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "maquinas_bloqueadas": ["cinta-02", "trituradora-01"]
    }


def test_corrupt_json_raises_store_error(path):
    path.parent.mkdir(parents=True)
    path.write_text("{esto no es json", encoding="utf-8")
    with pytest.raises(LockoutStoreError):
        JsonFileLockoutStore(path).load()


@pytest.mark.parametrize(
    "content",
    [
        '["trituradora-01"]',  
        '{"otra_clave": []}',  
        '{"maquinas_bloqueadas": "cinta-02"}',  
        '{"maquinas_bloqueadas": [1, 2]}',  
    ],
)
def test_unexpected_format_raises_store_error(path, content):
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LockoutStoreError):
        JsonFileLockoutStore(path).load()


def test_unreadable_path_raises_store_error(tmp_path):
    with pytest.raises(LockoutStoreError):
        JsonFileLockoutStore(tmp_path).load()


def test_unwritable_path_raises_store_error(tmp_path):
    blocker = tmp_path / "soy-un-fichero"
    blocker.write_text("", encoding="utf-8")
    with pytest.raises(LockoutStoreError):
        JsonFileLockoutStore(blocker / "candados.json").save({"cinta-02"})