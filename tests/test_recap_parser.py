"""
Tests for Ekumen Play Recap parser.
"""

from ekumen.services.runner import parse_play_recap


def test_parse_play_recap_standard():
    """Test parsing standard Ansible recap output."""
    output = """
    PLAY [all] *********************************************************************
    
    TASK [Gathering Facts] *********************************************************
    ok: [192.168.1.10]
    ok: [192.168.1.11]
    
    TASK [Install Nginx] ***********************************************************
    changed: [192.168.1.10]
    failed: [192.168.1.11]
    
    PLAY RECAP *********************************************************************
    192.168.1.10               : ok=5    changed=2    unreachable=0    failed=0    skipped=1
    192.168.1.11               : ok=1    changed=0    unreachable=0    failed=1    skipped=0
    """

    recap = parse_play_recap(output)
    assert recap['ok'] == 6
    assert recap['changed'] == 2
    assert recap['unreachable'] == 0
    assert recap['failed'] == 1
    assert recap['skipped'] == 1

    assert '192.168.1.10' in recap['hosts']
    assert recap['hosts']['192.168.1.10']['changed'] == 2
    assert recap['hosts']['192.168.1.11']['failed'] == 1


def test_parse_play_recap_unreachable():
    """Test recap parsing with unreachable hosts."""
    output = """
    PLAY RECAP *********************************************************************
    node-dead.lan              : ok=0    changed=0    unreachable=1    failed=0
    """
    recap = parse_play_recap(output)
    assert recap['unreachable'] == 1
    assert recap['ok'] == 0


def test_parse_play_recap_empty():
    """Test empty output handling."""
    recap = parse_play_recap("")
    assert recap['ok'] == 0
    assert recap['changed'] == 0
    assert recap['failed'] == 0
    assert len(recap['hosts']) == 0
