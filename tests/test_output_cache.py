"""
Tests for Ekumen OutputCache service.
"""

from ekumen.services.output_cache import OutputCache


def test_output_cache_store_and_retrieve(temp_dirs):
    """Test storing and retrieving output strings."""
    cache = OutputCache(cache_dir=temp_dirs['cache_dir'])

    content = "PLAY [all] ***\nok: [host1]\n"
    run_id = cache.store(content)
    assert run_id is not None

    # Retrieve latest
    latest_content, ts = cache.get_latest()
    assert latest_content == content
    assert ts is not None

    # Retrieve by ID
    byId_content, retrieved_id = cache.get_by_id(run_id)
    assert byId_content == content


def test_output_cache_empty(temp_dirs):
    """Test retrieving from empty cache."""
    cache = OutputCache(cache_dir=temp_dirs['cache_dir'])
    content, ts = cache.get_latest()
    assert content == ''
    assert ts == ''
