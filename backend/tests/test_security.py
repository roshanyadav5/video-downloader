import pytest

from app.services import security


class TestValidatePlatform:
    def test_accepts_known_platform(self):
        assert security.validate_platform("https://www.youtube.com/watch?v=abc") == "www.youtube.com"

    def test_accepts_short_domain_form(self):
        assert security.validate_platform("https://youtu.be/abc") == "youtu.be"

    def test_rejects_unknown_domain(self):
        with pytest.raises(security.UnsupportedURLError):
            security.validate_platform("https://example.com/video")

    def test_rejects_non_http_scheme(self):
        with pytest.raises(security.UnsupportedURLError):
            security.validate_platform("ftp://youtube.com/video")

    def test_rejects_file_scheme(self):
        with pytest.raises(security.UnsupportedURLError):
            security.validate_platform("file:///etc/passwd")

    def test_rejects_malformed_url(self):
        with pytest.raises(security.UnsupportedURLError):
            security.validate_platform("not a url at all")

    def test_lookalike_domain_is_rejected(self):
        # youtube.com.evil.com is NOT youtube.com — must not be accepted
        # via naive substring matching.
        with pytest.raises(security.UnsupportedURLError):
            security.validate_platform("https://youtube.com.evil.com/watch")

    def test_subdomain_of_allowed_domain_is_accepted(self):
        assert security.validate_platform("https://m.youtube.com/watch?v=abc") == "m.youtube.com"


class TestAssertSafeDestination:
    def test_rejects_localhost(self):
        with pytest.raises(security.UnsafeURLError):
            security.assert_safe_destination("localhost")

    def test_rejects_loopback_ip_literal(self):
        with pytest.raises(security.UnsafeURLError):
            security.assert_safe_destination("127.0.0.1")

    def test_rejects_cloud_metadata_ip(self):
        with pytest.raises(security.UnsafeURLError):
            security.assert_safe_destination("169.254.169.254")

    def test_rejects_private_range(self):
        with pytest.raises(security.UnsafeURLError):
            security.assert_safe_destination("10.0.0.5")


class TestSanitizeFilename:
    def test_strips_path_separators(self):
        assert "/" not in security.sanitize_filename("../../etc/passwd")
        assert "\\" not in security.sanitize_filename("..\\..\\windows\\system32")

    def test_strips_control_characters(self):
        result = security.sanitize_filename("video\x00\x1f.mp4")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_empty_input_gets_fallback(self):
        assert security.sanitize_filename("") == "download"

    def test_enforces_max_length(self):
        result = security.sanitize_filename("a" * 500, max_length=150)
        assert len(result) <= 150


class TestDetectPlatform:
    def test_detects_youtube(self):
        assert security.detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"

    def test_detects_youtube_short_domain(self):
        assert security.detect_platform("https://youtu.be/abc") == "youtube"

    def test_detects_facebook(self):
        assert security.detect_platform("https://www.facebook.com/reel/123") == "facebook"

    def test_detects_facebook_via_fb_watch(self):
        assert security.detect_platform("https://fb.watch/abc/") == "facebook"

    def test_detects_tiktok(self):
        assert security.detect_platform("https://www.tiktok.com/@user/video/123") == "tiktok"

    def test_unknown_domain_returns_unknown(self):
        assert security.detect_platform("https://example.com/video") == "unknown"

    def test_malformed_url_returns_unknown(self):
        assert security.detect_platform("not a url") == "unknown"
