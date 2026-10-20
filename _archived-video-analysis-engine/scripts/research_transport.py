#!/usr/bin/env python3
"""S9-0 offline research transport contract.

Defines the *shape* of a research query executor without ever opening a socket.
No engine selection, HTTP, credential handling, env lookup, or provider
registration lives here — only:

* :class:`ResearchQueryExecutor`, the injected transport Protocol the WRR
  adapter types against;
* :class:`ResearchExecutorError`, a failure that exposes only a stable, public
  ``code`` and never the private cause;
* :class:`ScriptedSuccess` / :class:`ScriptedFailure`, immutable scripted steps;
* :class:`ScriptedResearchExecutor`, a deterministic offline double.

The executor owns exactly one call per query — retries, engine selection, and
evidence promotion belong to WRR and the S5 validator, not to this seam.
"""
from __future__ import annotations

from typing import List, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ResearchQueryExecutor(Protocol):
    """Injected transport seam: map one plan query to a raw discovery result.

    The executor is *called* with a single immutable-plan query rendered as a
    plain mapping and returns a raw discovery mapping. It never retries, selects
    an engine, or promotes evidence; the WRR adapter invokes it exactly once per
    query and treats the return value as untrusted.
    """

    def __call__(self, query: Mapping[str, object]) -> Mapping[str, object]:
        ...


class ResearchExecutorError(Exception):
    """Transport failure exposing only a stable, non-secret ``code``.

    The private cause is deliberately withheld: it is never stored on the
    instance, never rendered by ``str``/``repr``, and the executor raises it
    ``from None`` so no exception chain or traceback can leak provider
    internals.
    """

    def __init__(self, code: str) -> None:
        self._code = str(code)
        super().__init__(self._code)

    @property
    def code(self) -> str:
        return self._code

    def __str__(self) -> str:
        return self._code

    def __repr__(self) -> str:
        return f"ResearchExecutorError(code={self._code!r})"


class ScriptedSuccess:
    """A scripted successful transport step: a raw discovery mapping.

    The mapping is copied defensively so a caller mutating the returned result
    cannot rewrite the script.
    """

    def __init__(self, result: Mapping[str, object]) -> None:
        self._result = dict(result)

    @property
    def result(self) -> dict:
        return dict(self._result)

    def __repr__(self) -> str:
        return f"ScriptedSuccess(keys={sorted(self._result)!r})"


class ScriptedFailure:
    """A scripted transport failure: exposes ``code``, hides ``private_error``.

    ``private_error`` models a provider-internal detail (a URL carrying a token,
    a credential, a raw upstream message). It is stored only so the executor can
    drop it on the floor — it is never surfaced through ``repr``, ``str``, or the
    raised :class:`ResearchExecutorError`.
    """

    def __init__(self, code: str, private_error: str) -> None:
        self._code = str(code)
        self._private_error = str(private_error)

    @property
    def code(self) -> str:
        return self._code

    def __repr__(self) -> str:
        # No ``private_error``: repr must never leak the private cause.
        return f"ScriptedFailure(code={self._code!r})"


class ScriptedResearchExecutor:
    """Deterministic offline double for :class:`ResearchQueryExecutor`.

    Consumes one scripted step per call, in order, recording every query in
    ``calls``. A :class:`ScriptedSuccess` returns its raw mapping; a
    :class:`ScriptedFailure` raises ``ResearchExecutorError(code) from None`` so
    the private cause is severed from the traceback. Any call beyond the script
    fails deterministically with a fixed ``executor_exhausted`` code — never an
    ``IndexError`` and never a leak.
    """

    _EXHAUSTED_CODE = "executor_exhausted"

    def __init__(self, script) -> None:
        self._script = list(script)
        self._cursor = 0
        self.calls: List[dict] = []

    def __call__(self, query: Mapping[str, object]) -> Mapping[str, object]:
        # Record every attempt first, so over-runs are observable too.
        self.calls.append(dict(query))
        if self._cursor >= len(self._script):
            raise ResearchExecutorError(self._EXHAUSTED_CODE) from None
        step = self._script[self._cursor]
        self._cursor += 1
        if isinstance(step, ScriptedFailure):
            raise ResearchExecutorError(step.code) from None
        if isinstance(step, ScriptedSuccess):
            return step.result
        # An unknown scripted step is a programming error in the test, but we
        # still fail deterministically rather than leak an arbitrary object.
        raise ResearchExecutorError(self._EXHAUSTED_CODE) from None


__all__ = [
    "ResearchQueryExecutor",
    "ResearchExecutorError",
    "ScriptedSuccess",
    "ScriptedFailure",
    "ScriptedResearchExecutor",
]
