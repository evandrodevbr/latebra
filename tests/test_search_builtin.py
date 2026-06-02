"""Tests for built-in search engines."""

import pytest


def test_base_search_engine_import():
    """BaseSearchEngine should be importable."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert BaseSearchEngine is not None


def test_base_search_engine_has_search_method():
    """BaseSearchEngine should define search method."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert hasattr(BaseSearchEngine, "search")


def test_base_search_engine_is_abstract():
    """BaseSearchEngine should not be instantiable directly."""
    from latebra.layers.search_builtin import BaseSearchEngine
    with pytest.raises(TypeError):
        BaseSearchEngine()
