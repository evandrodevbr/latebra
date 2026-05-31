"""Test pre-compiled stealth init script optimization."""


def test_browser_layer_has_compiled_stealth_script():
    """Browser layer should compile stealth script once, not per call."""
    from latebra.layers.browser import AsyncBrowserLayer

    # RED: the module should have a pre-compiled stealth string constant
    assert hasattr(AsyncBrowserLayer, "_STEALTH_SCRIPT"), (
        "Missing _STEALTH_SCRIPT — pre-compile stealth init script"
    )
    script = AsyncBrowserLayer._STEALTH_SCRIPT
    assert isinstance(script, str)
    assert "webdriver" in script
    assert "plugins" in script
    assert "chrome" in script


def test_stealth_script_constant_is_used():
    """The _scrape_patchright method should use _STEALTH_SCRIPT constant."""
    import inspect
    from latebra.layers.browser import AsyncBrowserLayer

    source = inspect.getsource(AsyncBrowserLayer._scrape_patchright)
    # Should reference the class constant, not inline the script string
    assert "_STEALTH_SCRIPT" in source or "self._STEALTH_SCRIPT" in source, (
        "scrape_patchright should use pre-compiled _STEALTH_SCRIPT"
    )
