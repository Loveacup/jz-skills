"""Storage analysis is an observational CLI, independent of cleanup approval."""
import json

import mac_doctor


def test_analyze_cli_reports_real_scoped_sizes_without_reading_file_contents(tmp_path, capsys):
    root = tmp_path / 'scope with spaces'
    root.mkdir()
    (root / 'small.dat').write_bytes(b's' * 1024)
    (root / 'large.dat').write_bytes(b'l' * 16384)
    before = {p.name: p.stat().st_mtime_ns for p in root.iterdir()}
    assert mac_doctor.main(['storage', 'analyze', '--root', str(root), '--min-mb', '0', '--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['read_only'] is True
    assert report['coverage']['complete'] is True
    assert report['top_consumers'][0]['path'] == str(root / 'large.dat')
    assert report['estimated_reclaimable_bytes'] is None
    assert {p.name: p.stat().st_mtime_ns for p in root.iterdir()} == before


def test_html_is_offline_escaped_and_never_overwrites_an_existing_file(tmp_path, capsys):
    import pytest
    root = tmp_path / 'scope'
    root.mkdir()
    (root / 'danger <img src=x onerror=alert(1)>.dat').write_bytes(b'x' * 4096)
    html = tmp_path / 'report.html'
    args = ['storage', 'analyze', '--root', str(root), '--min-mb', '0', '--json', '--html', str(html)]
    assert mac_doctor.main(args) == 0
    json.loads(capsys.readouterr().out)
    text = html.read_text()
    assert '<img src=x' not in text
    assert '&lt;img src=x' in text
    assert '<details>' in text and 'Content-Security-Policy' in text
    assert '<script' not in text and 'http://' not in text and 'https://' not in text
    assert html.stat().st_mode & 0o777 == 0o600
    saved = html.read_bytes()
    assert mac_doctor.main(args) == 2
    assert html.read_bytes() == saved


def test_hardlink_alias_is_visible_but_not_measured_or_ranked_twice(tmp_path):
    import os
    from macdoctor.storage_analysis import analyze
    (tmp_path / 'one').write_bytes(b'x' * 8192)
    os.link(tmp_path / 'one', tmp_path / 'two')
    calls = []
    def command(argv, timeout):
        calls.append(argv)
        if 'du' in argv[0]:
            return 0, '8\t' + argv[-1] + '\n', ''
        return 1, '', ''
    result = analyze([tmp_path], min_bytes=0, command=command)
    assert len([x for x in calls if 'du' in x[0]]) == 1
    assert len(result['top_consumers']) == 1
    aliases = [x for x in result['groups'][0]['items'] if x['status'] == 'excluded']
    assert len(aliases) == 1 and aliases[0]['reason'] == 'same_inode_alias'
