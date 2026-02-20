import pytest
from pydantic import ValidationError


class TestSourceType:
    def test_values(self):
        from app.domain.models.source import SourceType

        assert SourceType.github == "github"
        assert len(SourceType) == 1


class TestSourceCreate:
    def test_valid(self):
        from app.domain.models.source import SourceCreate, SourceType

        source = SourceCreate(
            type=SourceType.github,
            owner="ad-tech",
            repo="feature-pulse",
            token="ghp_abc123",
        )
        assert source.type == SourceType.github
        assert source.owner == "ad-tech"
        assert source.repo == "feature-pulse"
        assert source.token == "ghp_abc123"

    def test_token_default(self):
        from app.domain.models.source import SourceCreate, SourceType

        source = SourceCreate(
            type=SourceType.github,
            owner="ad-tech",
            repo="feature-pulse",
        )
        assert source.token == ""

    def test_invalid_type(self):
        from app.domain.models.source import SourceCreate

        with pytest.raises(ValidationError):
            SourceCreate(
                type="gitlab",
                owner="ad-tech",
                repo="feature-pulse",
            )


class TestSourceUpdate:
    def test_partial_dump(self):
        from app.domain.models.source import SourceUpdate

        update = SourceUpdate(active=False)
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"active": False}

    def test_token_update(self):
        from app.domain.models.source import SourceUpdate

        update = SourceUpdate(token="ghp_new_token")
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"token": "ghp_new_token"}

    def test_empty_update(self):
        from app.domain.models.source import SourceUpdate

        update = SourceUpdate()
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {}


class TestSource:
    def test_full(self):
        from app.domain.models.source import Source, SourceType

        source = Source(
            id="abc123def456",
            type=SourceType.github,
            owner="ad-tech",
            repo="feature-pulse",
            created_at="2026-02-20T10:00:00+09:00",
            token="ghp_abc123",
            active=True,
        )
        assert source.id == "abc123def456"
        assert source.active is True

    def test_defaults(self):
        from app.domain.models.source import Source, SourceType

        source = Source(
            id="abc123def456",
            type=SourceType.github,
            owner="ad-tech",
            repo="feature-pulse",
            created_at="2026-02-20T10:00:00+09:00",
        )
        assert source.token == ""
        assert source.active is True
