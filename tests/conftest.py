import pytest
from uuid import uuid4

from src.utils import namespace as namespace_module
from src.engine import engine as engine_module


@pytest.fixture(autouse=True)
def isolated_namespace(tmp_path, monkeypatch):
    """Every Edge() construction calls get_ns_uuid() unconditionally
    (see Edge._set_id in schemas.py), so tests need a valid namespace
    file without touching the project's real .sproutdb/ directory.

    engine.py imports SPROUTDB_DIR/NAMESPACE_FILE separately from
    namespace.py, so SproutDB() bootstrap needs its own patch target too."""
    namespace_file = tmp_path / "namespace.uuid"
    namespace_file.write_text(str(uuid4()), encoding="utf-8")
    monkeypatch.setattr(namespace_module, "NAMESPACE_FILE", str(namespace_file))
    monkeypatch.setattr(engine_module, "SPROUTDB_DIR", str(tmp_path))
    monkeypatch.setattr(engine_module, "NAMESPACE_FILE", str(namespace_file))
    yield
