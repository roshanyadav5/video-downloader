from app.services.url_normalizer import _needs_redirect_resolution, _strip_tracking_params, normalize_url


class TestStripTrackingParams:
    def test_strips_youtube_si_param(self):
        result = _strip_tracking_params("https://youtu.be/abc123?si=someTrackingValue")
        assert "si=" not in result
        assert "youtu.be/abc123" in result

    def test_strips_utm_params(self):
        result = _strip_tracking_params("https://www.youtube.com/watch?v=abc&utm_source=twitter&utm_medium=social")
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "v=abc" in result

    def test_strips_fbclid(self):
        result = _strip_tracking_params("https://www.facebook.com/watch/?v=123&fbclid=xyz")
        assert "fbclid" not in result
        assert "v=123" in result

    def test_preserves_essential_params(self):
        result = _strip_tracking_params("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert "v=dQw4w9WgXcQ" in result

    def test_no_params_unchanged(self):
        result = _strip_tracking_params("https://vimeo.com/12345")
        assert result == "https://vimeo.com/12345"


class TestNeedsRedirectResolution:
    def test_fb_watch_needs_resolution(self):
        assert _needs_redirect_resolution("https://fb.watch/abc123/") is True

    def test_facebook_share_link_needs_resolution(self):
        assert _needs_redirect_resolution("https://www.facebook.com/share/r/1QwLTdhdZr/") is True

    def test_facebook_share_video_link_needs_resolution(self):
        assert _needs_redirect_resolution("https://www.facebook.com/share/v/1QwLTdhdZr/") is True

    def test_pin_it_needs_resolution(self):
        assert _needs_redirect_resolution("https://pin.it/abc123") is True

    def test_normal_youtube_url_does_not_need_resolution(self):
        assert _needs_redirect_resolution("https://www.youtube.com/watch?v=abc") is False

    def test_normal_facebook_video_url_does_not_need_resolution(self):
        assert _needs_redirect_resolution("https://www.facebook.com/someuser/videos/12345/") is False

    def test_facebook_reel_does_not_need_resolution(self):
        assert _needs_redirect_resolution("https://www.facebook.com/reel/12345") is False


class TestNormalizeUrl:
    def test_plain_url_passes_through_cleaned(self):
        result = normalize_url("https://www.youtube.com/watch?v=abc&si=tracking123")
        assert result == "https://www.youtube.com/watch?v=abc"

    def test_does_not_attempt_network_call_for_normal_url(self):
        # If this tried to resolve a redirect for a normal URL, it would
        # hang/fail in this sandboxed, network-restricted test environment.
        # Successfully returning proves no redirect resolution was attempted.
        result = normalize_url("https://vimeo.com/12345?utm_source=test")
        assert result == "https://vimeo.com/12345"
