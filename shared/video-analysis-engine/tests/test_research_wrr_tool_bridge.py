# -*- coding: utf-8 -*-
"""S9-1 injectable WRR tool bridge contract.

Pins :class:`HermesWRRToolExecutor` — an injected ``SyncToolDispatcher`` seam
usable as :class:`HermesWRRAdapter`'s query executor. The bridge calls the
dispatcher exactly once per query with ``name='web_search'``, accepts only a
JSON string or a mapping envelope, and normalizes the ``details.results`` list
down to raw discovery keys. Nothing here opens a socket, forces a provider,
reads env/credentials, or promotes evidence — every failure surfaces only a
stable public code and never reflects the raw response or a secret.
"""
import ast
import json
import os

import pytest

import research_pipeline as rp
from research_transport import ResearchExecutorError
from research_wrr_tool_bridge import HermesWRRToolExecutor, SyncToolDispatcher


SECRET = "token=SUPER-SECRET-ac9931/private?key=leakme"


# ---------------------------------------------------------------------------
# Dispatcher doubles — record every call, never open a socket.
# ---------------------------------------------------------------------------
class RecordingDispatcher:
    """Return a scripted response and record each dispatch call verbatim."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def dispatch(self, name, args):
        self.calls.append((name, dict(args)))
        return self._response


class RaisingDispatcher:
    """Raise a caller-supplied exception (carrying a secret) on dispatch."""

    def __init__(self, exc):
        self._exc = exc
        self.calls = []

    def dispatch(self, name, args):
        self.calls.append((name, dict(args)))
        raise self._exc


def _query(**overrides):
    q = {"query_uid": "q-1", "mode": "grounding", "query": "检索增强生成 背景"}
    q.update(overrides)
    return q


def _envelope(results, *, success=True):
    return {"success": success, "details": {"results": list(results)}}


# ---------------------------------------------------------------------------
# Exactly one dispatch, exact args, no provider forcing.
# ---------------------------------------------------------------------------
def test_calls_dispatcher_exactly_once_with_web_search_and_bounded_args():
    dispatcher = RecordingDispatcher(_envelope([]))
    executor = HermesWRRToolExecutor(dispatcher, max_results=10)

    executor(_query())

    assert len(dispatcher.calls) == 1
    name, args = dispatcher.calls[0]
    assert name == "web_search"
    # Exact arg shape: query text, route mode, capped max_results — nothing else.
    assert args == {"query": "检索增强生成 背景", "mode": "grounding", "max_results": 10}


def test_args_never_force_a_provider_or_engine():
    dispatcher = RecordingDispatcher(_envelope([]))
    HermesWRRToolExecutor(dispatcher)(_query())

    _, args = dispatcher.calls[0]
    for forbidden in ("provider", "engine", "route", "credential", "api_key", "token"):
        assert forbidden not in args


def test_missing_mode_passes_none_without_extra_keys():
    dispatcher = RecordingDispatcher(_envelope([]))
    HermesWRRToolExecutor(dispatcher, max_results=3)(_query(mode=None))

    _, args = dispatcher.calls[0]
    assert args == {"query": "检索增强生成 背景", "mode": None, "max_results": 3}


# ---------------------------------------------------------------------------
# Good responses: JSON string + mapping, normalized and capped.
# ---------------------------------------------------------------------------
def test_json_string_response_is_parsed_and_normalized():
    payload = _envelope([
        {"url": "https://a.example/x", "title": "甲", "snippet": "s",
         "authority_relation": "primary"},
    ])
    dispatcher = RecordingDispatcher(json.dumps(payload))
    result = HermesWRRToolExecutor(dispatcher)(_query())

    candidates = result["results"]
    assert len(candidates) == 1
    assert candidates[0]["url"] == "https://a.example/x"
    assert candidates[0]["authority_relation"] == "primary"


def test_mapping_response_is_accepted_directly():
    payload = _envelope([
        {"url": "https://b.example/y", "content": "乙", "publisher": "P",
         "publisher_group": "G"},
    ])
    result = HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())

    assert result["results"][0]["url"] == "https://b.example/y"
    assert result["results"][0]["publisher"] == "P"
    assert result["results"][0]["publisher_group"] == "G"


def test_results_are_capped_at_max_results():
    payload = _envelope([{"url": f"https://x.example/{i}"} for i in range(25)])
    result = HermesWRRToolExecutor(RecordingDispatcher(payload), max_results=5)(_query())

    assert len(result["results"]) == 5
    assert [c["url"] for c in result["results"]] == [
        f"https://x.example/{i}" for i in range(5)
    ]


def test_empty_results_is_a_valid_empty_result():
    result = HermesWRRToolExecutor(RecordingDispatcher(_envelope([])))(_query())
    assert result["results"] == ()


# ---------------------------------------------------------------------------
# Normalization: only discovery keys survive; nothing is fabricated.
# ---------------------------------------------------------------------------
def test_unknown_keys_are_stripped_from_each_result():
    payload = _envelope([
        {"url": "https://a.example/x", "title": "甲",
         "raw_html": "<script>evil</script>", "api_key": SECRET,
         "__internal_cursor": "cursor-9931", "score": 0.9},
    ])
    result = HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())

    candidate = result["results"][0]
    assert set(candidate) <= {
        "url", "canonical_url", "title", "snippet", "content", "published_at",
        "source_kind", "authority_relation", "publisher", "publisher_group",
        "route", "provider", "provider_confidence",
    }
    assert "raw_html" not in candidate
    assert "api_key" not in candidate
    assert "__internal_cursor" not in candidate
    assert SECRET not in repr(candidate)


def test_does_not_fabricate_quote_snapshot_or_evidence():
    payload = _envelope([{"url": "https://a.example/x", "content": "内容"}])
    candidate = HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())["results"][0]

    for fabricated in ("quote_candidates", "quotes", "content_hash", "evidence",
                       "snapshot", "validation_status"):
        assert fabricated not in candidate


def test_malformed_and_nonmapping_results_are_skipped_not_raised():
    payload = _envelope([
        {"url": "https://good.example/1"},
        "not-a-mapping",
        12345,
        None,
        ["also", "not", "a", "mapping"],
        {"url": "https://good.example/2"},
    ])
    result = HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())

    urls = [c["url"] for c in result["results"]]
    assert urls == ["https://good.example/1", "https://good.example/2"]


# ---------------------------------------------------------------------------
# Failure paths: bounded, stable, secret-free.
# ---------------------------------------------------------------------------
def _assert_secret_free_executor_error(fn):
    with pytest.raises(ResearchExecutorError) as excinfo:
        fn()
    err = excinfo.value
    blob = str(err) + repr(err) + err.code
    assert SECRET not in blob
    assert err.__cause__ is None
    assert err.__suppress_context__ is True
    return err.code


def test_unsuccessful_response_raises_safe_error():
    payload = {"success": False, "details": {"reason": SECRET, "results": []}}
    code = _assert_secret_free_executor_error(
        lambda: HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())
    )
    assert code and isinstance(code, str)


def test_missing_details_results_raises_safe_error():
    for payload in (
        {"success": True},
        {"success": True, "details": {"note": SECRET}},
        {"success": True, "details": {"results": "not-a-list-" + SECRET}},
        {"success": True, "details": SECRET},
    ):
        _assert_secret_free_executor_error(
            lambda p=payload: HermesWRRToolExecutor(RecordingDispatcher(p))(_query())
        )


def test_nonmapping_nonstring_response_raises_safe_error():
    for payload in (12345, ["a", "list", SECRET], None, 3.14, b"bytes-" + SECRET.encode()):
        _assert_secret_free_executor_error(
            lambda p=payload: HermesWRRToolExecutor(RecordingDispatcher(p))(_query())
        )


def test_unparseable_json_string_raises_safe_error():
    payload = "{not valid json " + SECRET
    _assert_secret_free_executor_error(
        lambda: HermesWRRToolExecutor(RecordingDispatcher(payload))(_query())
    )


def test_json_string_that_is_not_an_object_raises_safe_error():
    # Valid JSON, but an array / scalar is not a success/details envelope.
    for payload in (json.dumps(["a", SECRET]), json.dumps("just-a-string-" + SECRET),
                    json.dumps(42)):
        _assert_secret_free_executor_error(
            lambda p=payload: HermesWRRToolExecutor(RecordingDispatcher(p))(_query())
        )


def test_oversized_string_response_fails_before_parsing():
    # A response longer than the bound must fail on size, before json.loads —
    # so an oversized *and* unparseable blob carrying a secret still stays safe.
    big = "x" * 200 + SECRET
    executor = HermesWRRToolExecutor(RecordingDispatcher(big), max_response_chars=64)
    _assert_secret_free_executor_error(lambda: executor(_query()))


def test_dispatcher_exception_is_redacted_to_stable_code():
    dispatcher = RaisingDispatcher(RuntimeError("upstream failed with " + SECRET))
    code = _assert_secret_free_executor_error(
        lambda: HermesWRRToolExecutor(dispatcher)(_query())
    )
    # Dispatcher was still invoked exactly once before the failure was redacted.
    assert len(dispatcher.calls) == 1
    assert code and isinstance(code, str)


# ---------------------------------------------------------------------------
# Integration: usable as HermesWRRAdapter's injected query executor.
# ---------------------------------------------------------------------------
def _one_query_plan():
    return rp.build_research_plan(
        evidence_bundle_hash="sha256:evidence",
        claim_bundle={"claim_bundle_semantic_hash": "sha256:" + "0" * 64, "claims": []},
        canonical_id="BV1", platform="bilibili", report_mode="full",
        research_policy="auto", capability_snapshot={"available": True},
        created_at="2026-07-14T00:00:00Z", plan_id="rp-one-query",
    )


def test_executor_drives_hermes_wrr_adapter_end_to_end():
    from research_wrr_adapter import HermesWRRAdapter

    plan = _one_query_plan()
    assert len(plan.queries) == 1

    payload = _envelope([
        {"url": "https://primary.example/a", "content": "甲",
         "authority_relation": "primary"},
    ])
    dispatcher = RecordingDispatcher(payload)
    executor = HermesWRRToolExecutor(dispatcher)

    raw = HermesWRRAdapter(executor).execute(plan)

    assert len(dispatcher.calls) == 1  # one query -> exactly one dispatch, no retry
    assert dispatcher.calls[0][0] == "web_search"
    assert raw.status == "completed"
    candidates = raw.raw_research["candidates"]
    assert candidates[0]["authority_relation"] == "primary"


def test_adapter_records_bridge_failure_once_without_secret():
    from research_wrr_adapter import HermesWRRAdapter

    plan = _one_query_plan()
    dispatcher = RaisingDispatcher(RuntimeError("boom " + SECRET))
    executor = HermesWRRToolExecutor(dispatcher)

    raw = HermesWRRAdapter(executor).execute(plan)

    assert len(dispatcher.calls) == 1
    assert raw.status == "failed"
    blob = repr(raw.errors) + repr(raw.raw_research)
    assert SECRET not in blob


def test_executor_satisfies_dispatcher_protocol_typing():
    assert isinstance(RecordingDispatcher(_envelope([])), SyncToolDispatcher)


# ---------------------------------------------------------------------------
# Static guard: the bridge imports no transport/tooling/env/socket machinery.
# ---------------------------------------------------------------------------
# ===========================================================================
# S9-3: explicit, opt-in fetch enrichment.
# ===========================================================================
import hashlib


def _sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FetchDispatcher:
    """Route ``web_fetch`` by URL to a scripted response; record every call."""

    def __init__(self, responses):
        self._responses = dict(responses)
        self.calls = []

    def dispatch(self, name, args):
        self.calls.append((name, dict(args)))
        if name == "web_fetch":
            return self._responses[args["url"]]
        raise AssertionError("unexpected tool " + name)

    @property
    def fetch_args(self):
        return [args for name, args in self.calls if name == "web_fetch"]


class RaisingFetchDispatcher:
    """Raise a caller-supplied exception (carrying a secret) on ``web_fetch``."""

    def __init__(self, exc):
        self._exc = exc
        self.calls = []

    def dispatch(self, name, args):
        self.calls.append((name, dict(args)))
        raise self._exc


def _fetch_envelope(url, text, highlights=(), *, success=True, chars="auto"):
    return {
        "success": success,
        "details": {
            "url": url,
            "text": text,
            "chars": len(text) if chars == "auto" else chars,
            "highlights": list(highlights),
        },
    }


# ---------------------------------------------------------------------------
# Opt-in: no fetch unless enrichment is explicitly requested.
# ---------------------------------------------------------------------------
def test_search_call_never_dispatches_web_fetch():
    dispatcher = RecordingDispatcher(_envelope([{"url": "https://a.example/x"}]))
    executor = HermesWRRToolExecutor(dispatcher)

    executor(_query())  # S9-1 search behavior, unchanged

    assert dispatcher.calls  # a dispatch did happen
    assert all(name == "web_search" for name, _ in dispatcher.calls)
    assert not any(name == "web_fetch" for name, _ in dispatcher.calls)


# ---------------------------------------------------------------------------
# Dedupe, cap, exact single-call args, no retry / provider forcing.
# ---------------------------------------------------------------------------
def test_enrich_dedupes_caps_and_fetches_each_retained_url_once():
    urls = [
        "https://a.example/1",
        "https://a.example/1",  # duplicate -> not re-fetched
        "https://b.example/2",
        "https://c.example/3",  # beyond cap -> never fetched
    ]
    responses = {u: _fetch_envelope(u, "内容-" + u) for u in urls}
    dispatcher = FetchDispatcher(responses)
    executor = HermesWRRToolExecutor(dispatcher, max_fetches=2, max_fetch_chars=1000)

    result = executor.enrich_selected_candidates([{"url": u} for u in urls])

    # Exactly two dispatches (retained, unique, capped), each once.
    assert dispatcher.fetch_args == [
        {"url": "https://a.example/1", "max_characters": 1000},
        {"url": "https://b.example/2", "max_characters": 1000},
    ]
    # No retry / provider / engine forcing: only url + bounded max_characters.
    for args in dispatcher.fetch_args:
        assert set(args) == {"url", "max_characters"}
    assert [item["url"] for item in result["enriched"]] == [
        "https://a.example/1",
        "https://b.example/2",
    ]
    assert result["errors"] == ()


def test_enrich_skips_noncanonical_urls_without_fetch_or_error():
    ok = "https://ok.example/a"
    dispatcher = FetchDispatcher({ok: _fetch_envelope(ok, "文本内容")})
    # max_fetches=1 makes budget consumption observable: if any invalid URL were
    # (wrongly) retained, the single slot would be spent before ``ok``.
    executor = HermesWRRToolExecutor(dispatcher, max_fetches=1)

    candidates = [
        {"url": "   "},                          # whitespace only
        {"url": "ftp://host/file"},              # non-http(s) scheme
        {"url": "/relative/path"},               # relative, no scheme
        {"url": "example.com/no-scheme"},        # bare host, no scheme
        {"url": "https://has space.example/x"},  # embedded whitespace
        {"url": "http://\thost/x"},              # embedded control char
        {"url": "http://"},                      # scheme but no netloc
        {"url": "https:///path"},                # empty netloc
        {"url": ok},                             # the one canonical URL
    ]
    result = executor.enrich_selected_candidates(candidates)

    # Only the canonical http(s) URL is fetched — zero fetch / zero error / zero
    # budget consumed on every invalid one.
    assert dispatcher.fetch_args == [{"url": ok, "max_characters": 20000}]
    assert [item["url"] for item in result["enriched"]] == [ok]
    assert result["errors"] == ()


def test_enrich_invalid_url_candidates_are_skipped_without_fetch():
    responses = {"https://ok.example/1": _fetch_envelope("https://ok.example/1", "文本")}
    dispatcher = FetchDispatcher(responses)
    executor = HermesWRRToolExecutor(dispatcher, max_fetches=5)

    result = executor.enrich_selected_candidates([
        {"title": "no url"},
        {"url": ""},
        {"url": 12345},
        "not-a-mapping",
        {"url": "https://ok.example/1"},
    ])

    assert dispatcher.fetch_args == [
        {"url": "https://ok.example/1", "max_characters": 20000},
    ]
    assert [item["url"] for item in result["enriched"]] == ["https://ok.example/1"]
    assert result["errors"] == ()


# ---------------------------------------------------------------------------
# Success: content / hash / full snapshot, allowlist-only, input untouched.
# ---------------------------------------------------------------------------
def test_success_builds_content_snapshot_hash_and_strips_unknown_fields():
    url = "https://a.example/x"
    text = "检索增强生成是一种结合外部知识的生成方法，用于事实核查。"
    dispatcher = FetchDispatcher({url: _fetch_envelope(url, text)})
    executor = HermesWRRToolExecutor(dispatcher)

    candidate = {
        "url": url, "title": "甲", "publisher": "P", "publisher_group": "G",
        "raw_html": "<script>evil</script>", "api_key": SECRET, "score": 0.9,
    }
    result = executor.enrich_selected_candidates([candidate])

    item = result["enriched"][0]
    h = _sha256_hex(text)
    assert item["url"] == url
    assert item["content"] == text
    assert item["content_sha256"] == h
    assert item["snapshot"] == {"content": text, "content_sha256": h, "mode": "full"}
    # content_sha256 is the SAME text hash in both places (no second protocol).
    assert item["snapshot"]["content_sha256"] == item["content_sha256"]
    # Only discovery allowlist fields survive; unknown / secret fields are gone.
    assert item["title"] == "甲" and item["publisher"] == "P"
    assert "raw_html" not in item and "api_key" not in item and "score" not in item
    assert SECRET not in repr(item)
    # Input mapping is not mutated in place.
    assert "content" not in candidate and "snapshot" not in candidate
    assert "quote_candidates" not in candidate


# ---------------------------------------------------------------------------
# Quote candidates: exact highlights only, first offset, dedupe, order kept.
# ---------------------------------------------------------------------------
def test_exact_highlights_become_quote_candidates_nonexact_omitted():
    url = "https://a.example/x"
    text = "alpha beta gamma beta delta"  # 'beta' twice -> first offset only
    highlights = ["beta", "beta", "gamma", "not-present", "", 123, None]
    dispatcher = FetchDispatcher({url: _fetch_envelope(url, text, highlights)})
    executor = HermesWRRToolExecutor(dispatcher)

    item = executor.enrich_selected_candidates([{"url": url}])["enriched"][0]
    quotes = item["quote_candidates"]

    # Deduplicated, upstream order preserved, non-exact/empty/non-str omitted.
    assert [q["quote_text"] for q in quotes] == ["beta", "gamma"]
    beta = quotes[0]
    assert beta["start"] == text.find("beta") and beta["start"] == 6
    assert text[beta["start"]:beta["end"]] == "beta"
    gamma = quotes[1]
    assert text[gamma["start"]:gamma["end"]] == "gamma"


def test_no_highlights_yields_empty_quote_candidates():
    url = "https://a.example/x"
    dispatcher = FetchDispatcher({url: _fetch_envelope(url, "文本内容", [])})
    item = HermesWRRToolExecutor(dispatcher).enrich_selected_candidates(
        [{"url": url}])["enriched"][0]
    assert item["quote_candidates"] == ()


# ---------------------------------------------------------------------------
# Fail-closed: malformed / unsuccessful / mismatched inputs never leak.
# ---------------------------------------------------------------------------
def _enrich_failure(response, url="https://req.example/path"):
    dispatcher = FetchDispatcher({url: response})
    result = HermesWRRToolExecutor(dispatcher).enrich_selected_candidates([{"url": url}])
    assert result["enriched"] == ()
    assert len(result["errors"]) == 1
    code = result["errors"][0]
    assert isinstance(code, str) and code
    assert SECRET not in repr(result)
    return code


def test_unsuccessful_fetch_fails_closed_without_leak():
    resp = {"success": False, "details": {"reason": SECRET, "text": SECRET}}
    assert _enrich_failure(resp)


def test_nonmapping_nonstring_response_fails_closed():
    for resp in (12345, ["a", SECRET], None, 3.14, b"bytes-" + SECRET.encode()):
        assert _enrich_failure(resp)


def test_unparseable_json_string_response_fails_closed():
    assert _enrich_failure("{not valid json " + SECRET)


def test_chars_mismatch_fails_closed_without_leaking_text():
    url = "https://req.example/path"
    text = "机密文本 " + SECRET
    resp = _fetch_envelope(url, text, chars=len(text) + 7)  # wrong count
    assert _enrich_failure(resp, url=url)


def test_url_mismatch_fails_closed_without_leaking_url():
    url = "https://req.example/path"
    resp = _fetch_envelope("https://evil.example/" + SECRET, "text")
    assert _enrich_failure(resp, url=url)


def test_empty_or_nonstring_text_fails_closed():
    url = "https://req.example/path"
    assert _enrich_failure(_fetch_envelope(url, "", []), url=url)  # empty text
    bad = {"success": True, "details": {"url": url, "text": 123, "chars": 3,
                                        "highlights": []}}
    assert _enrich_failure(bad, url=url)


def test_nonsequence_highlights_fails_closed():
    url = "https://req.example/path"
    bad = {"success": True, "details": {"url": url, "text": "abc", "chars": 3,
                                        "highlights": "not-a-list-" + SECRET}}
    assert _enrich_failure(bad, url=url)


def test_dispatcher_exception_is_redacted_to_stable_code():
    url = "https://req.example/path"
    dispatcher = RaisingFetchDispatcher(RuntimeError("upstream " + SECRET))
    result = HermesWRRToolExecutor(dispatcher).enrich_selected_candidates([{"url": url}])

    assert result["enriched"] == ()
    assert len(result["errors"]) == 1 and isinstance(result["errors"][0], str)
    assert len(dispatcher.calls) == 1  # invoked once, then redacted
    assert SECRET not in repr(result)


# ---------------------------------------------------------------------------
# Isolation: one candidate failing never affects the others.
# ---------------------------------------------------------------------------
def test_partial_failure_isolates_and_others_still_enrich():
    good = "https://good.example/1"
    bad = "https://bad.example/2"
    good2 = "https://good.example/3"
    responses = {
        good: _fetch_envelope(good, "第一条可核验内容"),
        bad: {"success": False, "details": {"reason": SECRET}},
        good2: _fetch_envelope(good2, "第三条可核验内容"),
    }
    dispatcher = FetchDispatcher(responses)
    executor = HermesWRRToolExecutor(dispatcher, max_fetches=5)

    result = executor.enrich_selected_candidates(
        [{"url": good}, {"url": bad}, {"url": good2}]
    )

    assert [item["url"] for item in result["enriched"]] == [good, good2]
    assert len(result["errors"]) == 1
    assert SECRET not in repr(result)


def test_bridge_imports_no_tools_wrr_http_os_or_socket():
    here = os.path.dirname(__file__)
    source_path = os.path.join(here, "..", "scripts", "research_wrr_tool_bridge.py")
    with open(source_path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read())

    forbidden = {
        "os", "sys", "socket", "ssl", "http", "urllib", "urllib2", "requests",
        "httpx", "aiohttp", "subprocess", "tools", "wrr",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])

    leaked = imported & forbidden
    assert not leaked, f"bridge must not import {sorted(leaked)}"
    # No dotted router/registry reach-throughs either.
    for name in imported:
        assert "router" not in name and "registry" not in name
