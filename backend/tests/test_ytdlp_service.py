import os
import tempfile
import time

import pytest

from app.config import get_settings
from app.services import ytdlp_service


@pytest.fixture(autouse=True)
def _reset_cookie_cache():
    """Each test gets a clean slate — module-level cache would otherwise
    leak state between tests since it's process-global by design."""
    ytdlp_service._writable_cookiefile_cache = None
    ytdlp_service._cached_source_mtime = None
    yield
    ytdlp_service._writable_cookiefile_cache = None
    ytdlp_service._cached_source_mtime = None
    os.environ.pop("COOKIES_FILE", None)
    get_settings.cache_clear()


def _write_cookie_file(path: str, marker: str) -> None:
    with open(path, "w") as f:
        f.write(f"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1999999999\tMARKER\t{marker}\n")


class TestWritableCookiefile:
    def test_returns_none_when_not_configured(self):
        os.environ.pop("COOKIES_FILE", None)
        get_settings.cache_clear()
        assert ytdlp_service._get_writable_cookiefile() is None

    def test_returns_none_when_configured_path_does_not_exist(self):
        os.environ["COOKIES_FILE"] = "/nonexistent/cookies.txt"
        get_settings.cache_clear()
        assert ytdlp_service._get_writable_cookiefile() is None

    def test_copies_to_a_writable_location(self, tmp_path):
        source = tmp_path / "cookies.txt"
        _write_cookie_file(str(source), "v1")
        os.environ["COOKIES_FILE"] = str(source)
        get_settings.cache_clear()

        writable_path = ytdlp_service._get_writable_cookiefile()

        assert writable_path is not None
        assert writable_path != str(source)
        assert os.access(writable_path, os.W_OK)
        assert "v1" in open(writable_path).read()

    def test_works_when_source_is_read_only(self, tmp_path):
        # This is the exact Render failure mode: source file mounted
        # read-only. Copying it elsewhere must not require write access
        # to the source's directory or the source file itself.
        source = tmp_path / "cookies.txt"
        _write_cookie_file(str(source), "v1")
        os.chmod(source, 0o444)
        os.chmod(tmp_path, 0o555)
        os.environ["COOKIES_FILE"] = str(source)
        get_settings.cache_clear()

        try:
            writable_path = ytdlp_service._get_writable_cookiefile()
            assert writable_path is not None
            assert os.access(writable_path, os.W_OK)
        finally:
            os.chmod(tmp_path, 0o755)
            os.chmod(source, 0o644)

    def test_refreshes_when_source_changes(self, tmp_path):
        source = tmp_path / "cookies.txt"
        _write_cookie_file(str(source), "v1")
        os.environ["COOKIES_FILE"] = str(source)
        get_settings.cache_clear()

        path1 = ytdlp_service._get_writable_cookiefile()
        assert "v1" in open(path1).read()

        time.sleep(0.02)
        _write_cookie_file(str(source), "v2")

        path2 = ytdlp_service._get_writable_cookiefile()
        content = open(path2).read()
        assert "v2" in content
        assert "v1" not in content

    def test_does_not_recopy_when_source_unchanged(self, tmp_path):
        source = tmp_path / "cookies.txt"
        _write_cookie_file(str(source), "v1")
        os.environ["COOKIES_FILE"] = str(source)
        get_settings.cache_clear()

        path1 = ytdlp_service._get_writable_cookiefile()
        mtime_after_first_copy = os.path.getmtime(path1)

        time.sleep(0.02)
        path2 = ytdlp_service._get_writable_cookiefile()

        assert path1 == path2
        assert os.path.getmtime(path2) == mtime_after_first_copy
