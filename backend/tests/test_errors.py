from app.errors import ErrorCode, classify_ytdlp_error


def _classify(message: str, cookies_configured: bool = False):
    return classify_ytdlp_error(Exception(message), cookies_configured=cookies_configured)


class TestClassifyYtdlpError:
    def test_no_suitable_extractor(self):
        err = _classify("ERROR: No suitable extractor found for URL https://example.com/x")
        assert err.error_code == ErrorCode.UNSUPPORTED_EXTRACTOR
        assert err.status_code == 422

    def test_private_video(self):
        err = _classify("ERROR: Private video")
        assert err.error_code == ErrorCode.PRIVATE_VIDEO

    def test_age_restricted(self):
        err = _classify("ERROR: This video is age restricted")
        assert err.error_code == ErrorCode.AGE_RESTRICTED

    def test_removed_video(self):
        err = _classify("ERROR: Video unavailable")
        assert err.error_code == ErrorCode.VIDEO_REMOVED

    def test_region_locked(self):
        err = _classify("ERROR: The uploader has not made this video available in your country")
        assert err.error_code == ErrorCode.REGION_LOCKED

    def test_sign_in_without_cookies_is_bot_verification(self):
        err = _classify("Sign in to confirm you're not a bot", cookies_configured=False)
        assert err.error_code == ErrorCode.BOT_VERIFICATION

    def test_sign_in_with_cookies_is_cookie_expired(self):
        err = _classify("Sign in to confirm you're not a bot", cookies_configured=True)
        assert err.error_code == ErrorCode.COOKIE_EXPIRED

    def test_facebook_impersonation_needed(self):
        err = _classify("ERROR: Cannot parse data")
        assert err.error_code == ErrorCode.BOT_VERIFICATION

    def test_video_too_long(self):
        err = _classify("does not pass filter (duration <? 3600), skipping")
        assert err.error_code == ErrorCode.VIDEO_TOO_LONG

    def test_ffmpeg_missing(self):
        err = _classify("ffmpeg not found. Please install")
        assert err.error_code == ErrorCode.FFMPEG_MISSING
        assert err.status_code == 503

    def test_network_timeout(self):
        err = _classify("Connection timed out")
        assert err.error_code == ErrorCode.NETWORK_ERROR

    def test_unknown_falls_back_gracefully(self):
        err = _classify("some completely novel yt-dlp error we've never seen")
        assert err.error_code == ErrorCode.UNKNOWN
        # Never leak the raw exception text to the client.
        assert "novel yt-dlp error" not in err.message
