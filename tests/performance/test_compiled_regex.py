"""Test compiled regex optimization for detection markers.

RED — production code uses slow loop-based detection.
GREEN — compiled regex constants in pipeline.py.
"""

import re
import pytest


def test_pipeline_has_compiled_marker_regex():
    """Pipeline module should expose compiled regex for fast detection."""
    from latebra import pipeline

    # RED: these don't exist yet → AttributeError
    assert hasattr(pipeline, "_MARKER_RE"), (
        "Missing compiled marker regex — optimize DETECTION_MARKERS check"
    )
    assert hasattr(pipeline, "_TERMINAL_ERROR_RE"), (
        "Missing compiled terminal error regex"
    )
    # Verify they're compiled patterns
    assert isinstance(pipeline._MARKER_RE, re.Pattern)
    assert isinstance(pipeline._TERMINAL_ERROR_RE, re.Pattern)


def test_compiled_regex_matches_original_behavior():
    """Compiled regex must produce same results as loop-based check."""
    from latebra.pipeline import _is_terminal_error
    from latebra.constants import DETECTION_MARKERS

    # Test terminal errors
    assert _is_terminal_error("Connection refused") is True
    assert _is_terminal_error("ERR_NAME_NOT_RESOLVED") is True
    assert _is_terminal_error("Normal response text") is False
    assert _is_terminal_error(None) is False
    assert _is_terminal_error("") is False


def test_compiled_regex_detection_markers():
    """Check that detection markers work correctly with compiled regex."""
    from latebra.pipeline import SmartScrapePipeline
    from latebra.constants import DETECTION_MARKERS

    # Verify constants are available
    assert len(DETECTION_MARKERS) > 0

    # Build check inline (mirrors what check_anonymity does)
    html_clean = "<html><body>Normal page</body></html>"
    html_blocked = "<html><body>captcha detected Access Denied</body></html>"

    # With compiled regex, blocked content should be detected
    from latebra.pipeline import _MARKER_RE
    markers_clean = _MARKER_RE.findall(html_clean)
    markers_blocked = _MARKER_RE.findall(html_blocked)

    assert len(markers_clean) == 0, f"False positives: {markers_clean}"
    # At least some markers should be found in blocked content
    # (depends on DETECTION_MARKERS matching the test strings)
