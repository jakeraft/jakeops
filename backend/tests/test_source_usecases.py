import pytest

from app.domain.models.source import SourceCreate, SourceUpdate


@pytest.fixture
def usecases(tmp_path):
    from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
    from app.usecases.source_usecases import SourceUseCasesImpl
    repo = FileSystemSourceRepository(tmp_path / "sources")
    return SourceUseCasesImpl(repo)


class TestSourceCRUD:
    def test_create_source(self, usecases):
        body = SourceCreate(type="github", owner="jakeraft", repo="jakeops")
        result = usecases.create_source(body)
        assert len(result["id"]) == 12
        assert result["owner"] == "jakeraft"
        assert result["repo"] == "jakeops"
        assert result["type"] == "github"
        assert result["active"] is True
        assert result["token"] == ""

    def test_create_source_with_token_masks(self, usecases):
        body = SourceCreate(type="github", owner="tok", repo="repo", token="ghp_abcdefgh1234")
        result = usecases.create_source(body)
        assert result["token"] == "ghp_****1234"

    def test_create_source_duplicate(self, usecases):
        body = SourceCreate(type="github", owner="dup", repo="repo")
        usecases.create_source(body)
        result = usecases.create_source(body)
        assert "error" in result
        assert result["error"] == "duplicate"

    def test_list_sources_empty(self, usecases):
        assert usecases.list_sources() == []

    def test_list_sources(self, usecases):
        usecases.create_source(SourceCreate(type="github", owner="a", repo="r1"))
        usecases.create_source(SourceCreate(type="github", owner="a", repo="r2"))
        items = usecases.list_sources()
        assert len(items) == 2

    def test_list_sources_masks_token(self, usecases):
        usecases.create_source(SourceCreate(type="github", owner="m", repo="r", token="ghp_longtoken1234"))
        items = usecases.list_sources()
        assert items[0]["token"] == "ghp_****1234"

    def test_get_source(self, usecases):
        body = SourceCreate(type="github", owner="g", repo="r")
        created = usecases.create_source(body)
        source = usecases.get_source(created["id"])
        assert source is not None
        assert source["owner"] == "g"

    def test_get_source_not_found(self, usecases):
        assert usecases.get_source("nonexist") is None

    def test_update_source_toggle_active(self, usecases):
        created = usecases.create_source(SourceCreate(type="github", owner="u", repo="r"))
        updated = usecases.update_source(created["id"], SourceUpdate(active=False))
        assert updated is not None
        assert updated["active"] is False

    def test_update_source_token(self, usecases):
        created = usecases.create_source(SourceCreate(type="github", owner="ut", repo="r"))
        updated = usecases.update_source(created["id"], SourceUpdate(token="ghp_newtoken5678"))
        assert updated["token"] == "ghp_****5678"

    def test_update_source_not_found(self, usecases):
        assert usecases.update_source("nonexist", SourceUpdate(active=False)) is None

    def test_delete_source(self, usecases):
        created = usecases.create_source(SourceCreate(type="github", owner="d", repo="r"))
        assert usecases.delete_source(created["id"]) is True
        assert usecases.list_sources() == []

    def test_delete_source_not_found(self, usecases):
        assert usecases.delete_source("nonexist") is False
