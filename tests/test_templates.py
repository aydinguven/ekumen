"""
Tests for Ekumen built-in playbook templates.
"""

import yaml
from ekumen.services.templates import list_templates, get_template, PLAYBOOK_TEMPLATES


def test_list_templates():
    """Test template listing."""
    templates = list_templates()
    assert len(templates) >= 5
    ids = [t['id'] for t in templates]
    assert 'system_update' in ids
    assert 'nginx_setup' in ids
    assert 'docker_install' in ids


def test_get_template_and_yaml_validity():
    """Test getting single templates and verify YAML content validity."""
    for t in PLAYBOOK_TEMPLATES:
        fetched = get_template(t['id'])
        assert fetched is not None
        assert fetched['name'] == t['name']
        assert fetched['content'] == t['content']

        # Verify YAML content parses without error
        parsed = yaml.safe_load(fetched['content'])
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert 'tasks' in parsed[0] or 'hosts' in parsed[0]

    # Non-existent
    assert get_template('non_existent_template') is None
