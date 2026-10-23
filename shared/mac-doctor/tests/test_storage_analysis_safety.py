"""Report-level failure, coverage, accounting and attribution regressions."""
import json
import plistlib
import types

import pytest
from macdoctor.storage_analysis import analyze, default_roots


def ok(argv, timeout):
    if 'diskutil' in argv[0]:
        return 1, '', ''
    return 0, '4\t' + argv[-1] + '\n', ''


def test_du_partial_output_stays_unknown_not_zero_or_reclaimable(tmp_path):
    (tmp_path / 'data').mkdir()
    def command(argv, timeout):
        return (1, '8\tpartial\n', 'denied') if 'du' in argv[0] else (1, '', '')
    report = analyze([tmp_path], min_bytes=0, command=command)
    row = report['groups'][0]['items'][0]
    assert row['size_bytes'] is None and row['observed_lower_bound_bytes'] == 8192
    assert report['coverage']['complete'] is False
    assert report['top_consumers'] == [] and report['estimated_reclaimable_bytes'] is None


def test_permission_denied_is_an_explicit_coverage_gap(tmp_path, monkeypatch):
    from macdoctor import storage_analysis as storage
    original = storage.os.scandir
    def denied(path):
        if str(path) == str(tmp_path):
            raise PermissionError('private content')
        return original(path)
    monkeypatch.setattr(storage.os, 'scandir', denied)
    report = analyze([tmp_path], command=ok)
    assert not report['coverage']['complete']
    assert report['groups'][0]['omissions'] == ['permission_denied']
    assert 'private content' not in json.dumps(report)


def test_budget_exhaustion_stops_launching_subprocesses(tmp_path):
    calls = []
    times = iter(range(100))
    report = analyze([tmp_path], budget_seconds=1, clock=lambda: next(times),
                     command=lambda *a: calls.append(a))
    assert calls == []
    assert not report['coverage']['complete']
    assert report['groups'][0]['omissions'] == ['budget_exhausted']


def test_nested_groups_are_not_summed_and_top_entries_are_disjoint(tmp_path):
    nested = tmp_path / 'nested'
    nested.mkdir()
    (nested / 'data').write_bytes(b'x')
    calls = []
    def command(argv, timeout):
        calls.append(argv)
        return ok(argv, timeout)
    report = analyze([tmp_path, nested, nested], min_bytes=0, command=command)
    assert not any('du' in x[0] and x[-1] == str(nested) for x in calls)
    assert len(report['groups']) == 2
    assert report['accounting']['additive'] is False
    assert [r['path'] for r in report['top_consumers']] == [str(nested / 'data')]


def test_symlinks_are_visible_exclusions_and_root_aliases_are_refused(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'link').symlink_to(tmp_path)
    report = analyze([root], min_bytes=0, command=ok)
    assert report['groups'][0]['items'][0]['reason'] == 'symlink'
    assert report['top_consumers'] == []
    alias = tmp_path / 'alias'
    alias.symlink_to(root)
    rejected = analyze([alias], min_bytes=0, command=ok)
    assert not rejected['coverage']['complete']
    assert rejected['groups'][0]['omissions'] == ['symlinked_root']


def test_app_metadata_identifies_container_but_does_not_authorize_cleanup(tmp_path):
    containers = tmp_path / 'Library/Containers'
    container = containers / 'opaque-id'
    container.mkdir(parents=True)
    (container / '.com.apple.containermanagerd.metadata.plist').write_bytes(
        plistlib.dumps({'MCMMetadataIdentifier': 'com.example.application'}))
    report = analyze([containers], home=tmp_path, min_bytes=0, command=ok)
    item = report['top_consumers'][0]
    assert item['owner_bundle_id'] == 'com.example.application'
    assert item['risk'] == 'protected_review'
    assert report['estimated_reclaimable_bytes'] is None


def test_models_and_toolchains_never_become_auto_cleanable_by_directory_name(tmp_path):
    for name in ['.cargo', '.docker', '.cache']:
        (tmp_path / name).mkdir()
    report = analyze([tmp_path], home=tmp_path, min_bytes=0, command=ok)
    assert all(row['risk'] == 'protected_review' for row in report['top_consumers'])


def test_apfs_zero_free_is_known_not_missing(tmp_path):
    def command(argv, timeout):
        return 0, plistlib.dumps({'APFSContainerFree': 0, 'APFSContainerSize': 1000}).decode(), ''
    disk = analyze([tmp_path], command=command)['system']['apfs']
    assert disk['status'] == 'ok' and disk['container_free_bytes'] == 0


def test_existing_storage_health_check_recognizes_a_completely_full_apfs_container():
    from macdoctor.checks import storage
    def command(argv, timeout):
        return 0, plistlib.dumps({'APFSContainerFree': 0, 'APFSContainerSize': 1000}).decode(), ''
    result = storage.apfs_free(command, 2)
    assert result.status == 'crit'
    assert result.value['free_bytes'] == 0


def test_explicit_missing_root_is_not_a_successful_complete_scan(tmp_path):
    report = analyze([tmp_path / 'missing'], command=ok)
    assert not report['coverage']['complete']


def test_corrupt_container_xml_does_not_destroy_cli_report(tmp_path, monkeypatch, capsys):
    import mac_doctor
    containers = tmp_path / 'Library/Containers'
    container = containers / 'corrupt-container'
    container.mkdir(parents=True)
    (container / '.com.apple.containermanagerd.metadata.plist').write_bytes(
        b'<?xml version="1.0"?><plist><dict><key>MCMMetadataIdentifier</key><string>truncated')
    monkeypatch.setenv('MAC_DOCTOR_HOME', str(tmp_path))
    assert mac_doctor.main(['storage', 'analyze', '--root', str(containers), '--min-mb', '0', '--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['top_consumers'][0]['path'] == str(container)
    assert report['top_consumers'][0]['owner_bundle_id'] is None
    assert report['read_only'] is True


def test_corrupt_apfs_xml_becomes_unknown_without_destroying_scan(tmp_path):
    report = analyze([tmp_path], command=lambda *a: (0, '<?xml version="1.0"?><plist><dict>', ''))
    assert report['system']['apfs']['status'] == 'unknown'
    assert report['coverage']['complete'] is True


def test_profile_redirected_home_does_not_change_account_default_roots(tmp_path, monkeypatch):
    from macdoctor import paths
    monkeypatch.delenv('MAC_DOCTOR_HOME', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path / 'profile-home'))
    monkeypatch.setattr(paths.pwd, 'getpwuid', lambda uid: types.SimpleNamespace(pw_dir=str(tmp_path / 'account')))
    roots = default_roots(paths.account_home())
    assert roots[0] == tmp_path / 'account'
    assert all('profile-home' not in str(p) for p in roots)


def test_invalid_budget_and_root_are_rejected_without_probing(tmp_path):
    for budget in [0, -1, float('nan'), float('inf'), 121, True]:
        with pytest.raises(ValueError):
            analyze([tmp_path], budget_seconds=budget, command=lambda *a: pytest.fail('must not probe'))
    with pytest.raises(ValueError):
        analyze(['relative'], command=lambda *a: pytest.fail('must not probe'))
