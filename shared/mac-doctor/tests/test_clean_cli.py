import argparse
import json

from macdoctor import cli_clean


def test_storage_json_accepts_report_only_snapshot_rows(monkeypatch, capsys):
    monkeypatch.setattr(cli_clean.clean, "scan", lambda: [
        {"class": "SAFE", "size_bytes": 1024},
        {"class": "REPORT", "count": 2, "dates": ["2026-10-01-120000"],
         "estimated_purgeable_bytes": "unknown", "manual_commands": ["tmutil deletelocalsnapshots 2026-10-01-120000"]},
        {"class": "SAFE", "size_bytes": "unknown"}])
    args = argparse.Namespace(json=True)
    assert cli_clean._storage(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["known_size_bytes"] == 1024
    assert output["unknown_size_count"] == 1
    assert output["report_only_count"] == 1
    assert output["items"][1]["manual_commands"][0] == "tmutil deletelocalsnapshots 2026-10-01-120000"
