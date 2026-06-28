"""WRR 异常层级。

EngineError 及其子类可触发 fallback；AllEnginesFailedError 表示整链失败。
注：超时类命名 EngineTimeoutError，避免遮蔽内建 TimeoutError。
"""


class WRRError(Exception):
    """所有 WRR 异常基类。"""


class EngineError(WRRError):
    """单引擎调用失败（可触发 fallback）。"""


class RateLimitError(EngineError):
    """引擎限流（HTTP 429/432 等），可触发 fallback。"""


class EngineTimeoutError(EngineError):
    """引擎超时（可触发 fallback）。"""


class AllEnginesFailedError(WRRError):
    """fallback 链全部 provider 失败。"""
