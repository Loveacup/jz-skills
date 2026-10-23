"""Offline HTML view only: no JavaScript, network assets or filesystem action server."""
from __future__ import annotations

import html
import os
from pathlib import Path


def _e(value):
    return html.escape(str(value), quote=True)


def _size(value):
    if type(value) is not int or value < 0:
        return '未知'
    n = float(value)
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if n < 1024 or unit == 'PiB':
            return f'{n:.1f} {unit}'
        n /= 1024


def _row(item):
    owner = item.get('owner_bundle_id') or '未核实'
    reason = item.get('reason') or ''
    return ('<article><div class="row"><strong>' + _e(item['name']) + '</strong><b>'
            + _e(_size(item.get('size_bytes'))) + '</b></div><code>' + _e(item['path'])
            + '</code><p>测量：' + _e(item['status']) + ' · 类型：' + _e(item.get('kind'))
            + ' · 处置：' + _e(item.get('risk')) + ' · 归属：' + _e(owner) + '</p><p>'
            + _e(item.get('recommendation') or '') + ' ' + _e(reason) + '</p></article>')


def render_html(report):
    disk = report['system']['apfs']
    coverage = report['coverage']
    total, free = disk.get('container_total_bytes'), disk.get('container_free_bytes')
    meter = ''
    if (disk.get('status') == 'ok' and type(total) is int and type(free) is int
            and total > 0 and 0 <= free <= total):
        meter = f'<meter min="0" max="{total}" value="{free}" aria-label="APFS container free space"></meter>'
    hotspots = ''.join(_row(row) for row in report['top_consumers']) or '<p>当前阈值和已完成范围内没有可排名记录；不表示磁盘没有大文件。</p>'
    groups = ''
    for group in report['groups']:
        groups += ('<details><summary>' + _e(group['root']) + ' — ' + _e(group['status'])
                   + '</summary><p>已枚举 ' + _e(group['entries_seen']) + ' 项；低于阈值 '
                   + _e(group['filtered_below_threshold']) + ' 项；缺口：'
                   + _e(', '.join(group['omissions']) or '无额外记录') + '</p>'
                   + ''.join(_row(row) for row in group['items']) + '</details>')
    notes = ''.join('<li>' + _e(note) + '</li>' for note in report['accounting']['notes'])
    status = '所选范围按声明策略完成' if coverage['complete'] else '扫描存在缺口，不能据此判断完整占用'
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>mac-doctor · 只读存储分析</title><style>
:root{color-scheme:light dark;font-family:system-ui,-apple-system,sans-serif;background:#111827;color:#e5e7eb}
body{max-width:1060px;margin:auto;padding:32px 20px;line-height:1.6}h1{font-size:2rem;letter-spacing:-.04em;margin-bottom:0}
small,code{color:#b6c5d9}code{display:block;overflow-wrap:anywhere;font-size:.85rem}.muted{color:#b6c5d9}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin:24px 0}
.card,article,details{background:#192335;border:1px solid #35445a;border-radius:12px;padding:16px;margin:12px 0}
.card b{display:block;font-size:1.6rem;color:#bfe4ff}.row{display:flex;justify-content:space-between;gap:16px;overflow-wrap:anywhere}
article p{font-size:.9rem;margin:8px 0 0}summary{cursor:pointer;overflow-wrap:anywhere}meter{width:100%;height:20px}
h2{margin-top:36px}.notice{border-left:4px solid #fbbf24;padding:12px 16px;background:#283044}li{margin:8px 0}
</style></head><body><small>MAC-DOCTOR / STORAGE ATTRIBUTION</small><h1>只读存储分析</h1><p class="muted">'''+ _e(report['generated_at']) + '''</p>
<p class="notice">''' + _e(status) + '''。本报告不执行清理；占用大小不是可释放空间，也不授予删除权限。</p>
<section class="cards"><div class="card">APFS 容器总量<b>''' + _e(_size(total)) + '''</b></div>
<div class="card">APFS 容器可用<b>''' + _e(_size(free)) + '''</b></div>
<div class="card">未知测量<b>''' + _e(coverage['unknown_measurements']) + '''</b></div>
<div class="card">可释放空间<b>未判定</b></div></section>''' + meter + '''<p>磁盘元信息：''' + _e(disk.get('status')) + ''' · ''' + _e(disk.get('volume_name') or '卷名未知') + '''</p>
<h2>已观察到的非重叠热点</h2>''' + hotspots + '''
<h2>范围与覆盖缺口</h2><p>预算 ''' + _e(coverage['budget_seconds']) + ''' 秒，耗时 ''' + _e(coverage['elapsed_seconds']) + ''' 秒；不完整范围：''' + _e(', '.join(coverage['incomplete_roots']) or '无') + '''</p>''' + groups + '''
<h2>解释与下一步</h2><ul>''' + notes + '''</ul><p>优先识别用途和归属；应用数据使用应用自带管理入口。需要清理时，另行核验精确目标、活跃使用与当前授权，沿用 mac-doctor 原有计划／审批流程。</p>
<footer class="muted">本地静态文件 · 无外部资源 · 无服务 · 无删除按钮</footer></body></html>'''


def write_html(report, filename):
    path = Path(filename)
    if not path.is_absolute():
        raise ValueError('HTML output must be an absolute new file path')
    content = render_html(report)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(content)
    return str(path)
