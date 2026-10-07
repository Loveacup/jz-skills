import argparse

from macdoctor import cli_jev


def test_ask_without_key_exits_two_without_collection(monkeypatch, capsys):
    monkeypatch.setattr(cli_jev, "_config", lambda: {"jev": {"enabled": True}})
    monkeypatch.setattr(cli_jev, "_collect", lambda: (_ for _ in ()).throw(AssertionError("collector should not run")))
    assert cli_jev._ask(argparse.Namespace(json=True)) == 2
    assert "no API key" in capsys.readouterr().err
