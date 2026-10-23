"""Bounded read-only storage attribution. Sizes are observations, never deletion grants."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import time
from xml.parsers.expat import ExpatError

from .paths import account_home
from .runner import CommandError, CommandTimeout, run


def default_roots(home):
    return [home, home / 'Library', home / 'Library/Caches',
            home / 'Library/Containers', home / 'Library/Group Containers',
            home / 'Library/Application Support', home / 'Downloads',
            home / 'Library/Developer', Path('/Applications')]


def _within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _first_int(value, *keys):
    return next((value[k] for k in keys if type(value.get(k)) is int and value[k] >= 0), None)


def _disk(command, timeout):
    try:
        rc, out, _ = command(['/usr/sbin/diskutil', 'info', '-plist', '/System/Volumes/Data'], timeout)
        info = plistlib.loads(out.encode() if isinstance(out, str) else out)
        if rc or not isinstance(info, dict):
            raise ValueError('disk metadata unavailable')
        free = _first_int(info, 'APFSContainerFree', 'ContainerFreeSpace')
        total = _first_int(info, 'APFSContainerSize', 'ContainerTotalSpace')
        return {'status': 'ok' if free is not None and total is not None and total > 0 and free <= total else 'unknown',
                'source': 'diskutil info -plist /System/Volumes/Data',
                'volume_name': info.get('VolumeName'), 'container': info.get('APFSContainerReference'),
                'container_free_bytes': free, 'container_total_bytes': total}
    except (CommandError, CommandTimeout, ValueError, TypeError, ExpatError, plistlib.InvalidFileException):
        return {'status': 'unknown', 'source': 'diskutil', 'container_free_bytes': None,
                'container_total_bytes': None}


def _guidance(path, home):
    """Classify only by known location; no catalogue mutation or automatic green tier."""
    for relative in ['Library/Containers', 'Library/Group Containers', 'Library/Application Support']:
        if _within(path, home / relative):
            return ('app_data', 'protected_review',
                    'Identify the owning app; use its storage controls. Do not delete container/profile databases.')
    if path.suffix == '.app':
        return ('application', 'managed_review', 'Review need and use the supported app uninstall route.')
    for relative in ['.npm/_cacache', 'Library/Caches/pip', 'Library/Caches/uv',
                     'Library/Developer/Xcode/DerivedData']:
        if _within(path, home / relative):
            return ('rebuildable_cache', 'review',
                    'Potentially regenerable; verify active use and exact scope before a separate cleanup plan.')
    if _within(path, home / '.Trash'):
        return ('trash', 'protected_review', 'Review recovery needs; moving here has not freed space. No emptying is authorized.')
    if _within(path, home / 'Downloads'):
        return ('downloads', 'review', 'Review original files and retention needs; age or extension is not deletion approval.')
    if any(_within(path, home / rel) for rel in ['.cargo', '.docker', '.gradle', '.m2', '.cache']):
        return ('developer_data', 'protected_review',
                'May contain toolchains, configuration, models or persistent volumes; inspect the exact subdirectory.')
    return ('unclassified', 'review', 'Identify purpose and owner before considering any cleanup.')


def _owner(path, home):
    # This is the sole optional content read: bounded system container identity metadata,
    # never a user document/database. Do not follow a symlink to another content file.
    if not any(path.parent == home / rel for rel in ['Library/Containers', 'Library/Group Containers']):
        return None
    meta = path / '.com.apple.containermanagerd.metadata.plist'
    try:
        st = meta.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > 262144:
            return None
        with meta.open('rb') as f:
            data = f.read(262145)
        if len(data) > 262144:
            return None
        value = plistlib.loads(data).get('MCMMetadataIdentifier')
        return value if isinstance(value, str) and len(value) <= 512 else None
    except (OSError, ValueError, TypeError, AttributeError, ExpatError, plistlib.InvalidFileException):
        return None


def analyze(roots=None, *, home=None, min_bytes=50 * 1024 * 1024, top=5,
            budget_seconds=30, max_entries=200, command=run, clock=time.monotonic):
    """Public report seam; injectable OS command/clock supports deterministic failure checks.

    Traversal is one level per requested root; du is recursive, -x, bounded per child.
    Nested requested roots reuse measurements and are not summed as freeable bytes.
    """
    if (type(top) is not int or not 1 <= top <= 100 or type(max_entries) is not int
            or not 1 <= max_entries <= 1000 or type(min_bytes) is not int or min_bytes < 0
            or not isinstance(budget_seconds, (int, float)) or isinstance(budget_seconds, bool)
            or not math.isfinite(budget_seconds) or not 0 < budget_seconds <= 120):
        raise ValueError('invalid scan limits')
    home = Path(home or account_home()).absolute()
    requested = list(roots) if roots is not None else default_roots(home)
    if not requested or len(requested) > 32:
        raise ValueError('provide between 1 and 32 roots')
    unique_roots = []
    for value in requested:
        p = Path(value)
        if not p.is_absolute() or '..' in p.parts:
            raise ValueError('roots must be absolute paths without parent traversal')
        if p not in unique_roots:
            unique_roots.append(p)
    start = clock()
    deadline = start + budget_seconds
    remaining = lambda: max(0.0, deadline - clock())
    disk = _disk(command, min(3.0, remaining())) if remaining() > 0 else {'status': 'unknown'}
    groups, measured, identities = [], {}, {}
    for root in unique_roots:
        group = {'root': str(root), 'status': 'ok', 'entries_seen': 0,
                 'filtered_below_threshold': 0, 'items': [], 'omissions': []}
        groups.append(group)
        try:
            # Refuse symlinked roots/ancestors instead of silently measuring a different tree.
            if any(p.is_symlink() for p in [root, *root.parents]):
                group.update(status='partial', omissions=['symlinked_root'])
                continue
            st = root.stat()
            if not stat.S_ISDIR(st.st_mode):
                group.update(status='partial', omissions=['not_directory'])
                continue
            if remaining() <= 0:
                group.update(status='partial', omissions=['budget_exhausted'])
                continue
            with os.scandir(root) as entries:
                for entry in entries:
                    if remaining() <= 0 or group['entries_seen'] >= max_entries:
                        group['status'] = 'partial'
                        group['omissions'].append('budget_exhausted' if remaining() <= 0 else 'entry_limit')
                        break
                    group['entries_seen'] += 1
                    path = Path(entry.path)
                    key = str(path)
                    if key in measured:
                        row = measured[key]
                    else:
                        row = {'path': key, 'name': entry.name, 'status': 'unknown', 'size_bytes': None,
                               'size_basis': 'du_allocated_kib', 'reason': None}
                        try:
                            child_stat = entry.stat(follow_symlinks=False)
                            if stat.S_ISLNK(child_stat.st_mode):
                                row.update(status='excluded', reason='symlink')
                            elif child_stat.st_dev != st.st_dev:
                                row.update(status='excluded', reason='different_filesystem')
                            elif path in unique_roots and stat.S_ISDIR(child_stat.st_mode):
                                row.update(status='expanded', reason='scanned_as_separate_root')
                            elif not (stat.S_ISREG(child_stat.st_mode) or stat.S_ISDIR(child_stat.st_mode)):
                                row.update(status='excluded', reason='special_file')
                            elif (child_stat.st_dev, child_stat.st_ino) in identities:
                                row.update(status='excluded', reason='same_inode_alias',
                                           duplicate_of=identities[(child_stat.st_dev, child_stat.st_ino)])
                            else:
                                rc, out, _ = command(['/usr/bin/du', '-skx', key], min(3.0, remaining()))
                                match = re.match(r'^(\d+)\s', out)
                                size = int(match.group(1)) * 1024 if match else None
                                if rc or size is None:
                                    row.update(status='partial' if size is not None else 'unknown',
                                               reason='du_failed_or_unreadable', observed_lower_bound_bytes=size)
                                else:
                                    row.update(status='ok', size_bytes=size)
                                    identities[(child_stat.st_dev, child_stat.st_ino)] = key
                        except CommandTimeout:
                            row['reason'] = 'timeout'
                        except (CommandError, OSError):
                            row['reason'] = 'measurement_unavailable'
                        kind, risk, action = _guidance(path, home)
                        row.update(kind=kind, risk=risk, recommendation=action,
                                   owner_bundle_id=_owner(path, home) if row['status'] == 'ok' else None)
                        measured[key] = row
                    if row['status'] in ('partial', 'unknown'):
                        group['status'] = 'partial'
                    if row['status'] == 'ok' and row['size_bytes'] < min_bytes:
                        group['filtered_below_threshold'] += 1
                    else:
                        group['items'].append(row)
        except FileNotFoundError:
            group['status'] = 'absent'
        except PermissionError:
            group.update(status='partial', omissions=['permission_denied'])
        except OSError:
            group.update(status='partial', omissions=['root_unavailable'])
        group['items'].sort(key=lambda r: (-(r['size_bytes'] or 0), r['path']))
    # Exclude broad aggregate rows when a detailed requested group is available.
    detailed = {g['root'] for g in groups if g['status'] in ('ok', 'partial') and g['entries_seen'] > 0}
    candidates = [r for r in measured.values() if r['status'] == 'ok'
                  and r['size_bytes'] >= min_bytes and r['path'] not in detailed]
    candidates.sort(key=lambda r: (-r['size_bytes'], r['path']))
    selected = []
    for row in candidates:
        p = Path(row['path'])
        if not any(_within(p, Path(x['path'])) or _within(Path(x['path']), p) for x in selected):
            selected.append(row)
            if len(selected) >= top:
                break
    unknown = sum(r['status'] in ('partial', 'unknown') for r in measured.values())
    incomplete = [g['root'] for g in groups if g['status'] == 'partial'
                  or (roots is not None and g['status'] == 'absent')]
    return {'schema_version': 'storage-analysis/v1', 'generated_at': datetime.now(timezone.utc).isoformat(),
            'read_only': True, 'system': {'apfs': disk}, 'groups': groups, 'top_consumers': selected,
            'estimated_reclaimable_bytes': None,
            'coverage': {'complete': not incomplete and not unknown, 'incomplete_roots': incomplete,
                         'unknown_measurements': unknown, 'observed_paths': len(measured),
                         'measured_paths': sum(r['status'] == 'ok' for r in measured.values()),
                         'excluded_paths': sum(r['status'] == 'excluded' for r in measured.values()),
                         'threshold_bytes': min_bytes, 'max_entries_per_root': max_entries,
                         'elapsed_seconds': round(clock() - start, 3), 'budget_seconds': budget_seconds},
            'accounting': {'additive': False, 'reclaimability': 'not_determined',
                           'notes': ['Nested groups overlap; do not add their sizes.',
                                     'Top consumers are disjoint observed hotspots, not a full-volume inventory.',
                                     'du allocated bytes may include shared/cloned blocks; not physical reclaimable space.',
                                     'APFS container free space is separate from directory attribution.',
                                     'Excluded symlinks, other filesystems and special files remain visible.',
                                     'No file cleanup, plan approval, server or cron change was performed.']}}
