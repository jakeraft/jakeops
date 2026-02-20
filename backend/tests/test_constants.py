from datetime import timezone, timedelta


def test_kst_offset():
    from app.domain.constants import KST

    assert KST == timezone(timedelta(hours=9))


def test_schema_version():
    from app.domain.constants import SCHEMA_VERSION

    assert SCHEMA_VERSION == 4


def test_id_length():
    from app.domain.constants import ID_HEX_LENGTH

    assert ID_HEX_LENGTH == 12
