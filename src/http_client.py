from __future__ import annotations

"""HTTP helper：優先用 curl_cffi 模擬瀏覽器 TLS。"""

from typing import Any, Optional

from .error_log import log_error

BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.taiwanlottery.com/lotto/history/result_download/",
    "Origin": "https://www.taiwanlottery.com",
}


class HttpClient:
    def __init__(self, timeout: float = 30.0, verify: bool = False):
        # 公司筆電常見自簽/攔截憑證，預設關閉驗證以免 curl: (60)
        self.timeout = timeout
        self.verify = verify
        self.backend = "requests"
        self._session: Any = None
        self._init_session()

    def _init_session(self) -> None:
        try:
            from curl_cffi import requests as curl_requests

            self._session = curl_requests.Session(impersonate="chrome")
            self.backend = "curl_cffi"
            try:
                self._session.trust_env = False
            except Exception:  # noqa: BLE001
                pass
            log_error(
                f"HTTP backend = curl_cffi (chrome), verify={self.verify}",
                context="HttpClient",
            )
            return
        except Exception as exc:  # noqa: BLE001
            log_error(
                "curl_cffi unavailable; fallback to requests (may be blocked by WAF)",
                exc,
                context="HttpClient",
            )

        import requests

        self._session = requests.Session()
        self._session.trust_env = False
        self._session.proxies = {"http": None, "https": None}
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                **BROWSER_HEADERS,
            }
        )
        self.backend = "requests"
        log_error(
            f"HTTP backend = requests, verify={self.verify}",
            context="HttpClient",
        )

    def get(
        self,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[float] = None,
    ):
        merged = dict(BROWSER_HEADERS)
        if headers:
            merged.update(headers)
        kwargs = {
            "params": params,
            "headers": merged,
            "timeout": timeout or self.timeout,
            "verify": self.verify,
        }
        if self.backend == "curl_cffi":
            try:
                return self._session.get(url, impersonate="chrome", **kwargs)
            except TypeError:
                # 舊版不支援某些參數
                kwargs.pop("verify", None)
                try:
                    return self._session.get(
                        url,
                        impersonate="chrome",
                        verify=self.verify,
                        params=params,
                        headers=merged,
                        timeout=timeout or self.timeout,
                    )
                except TypeError:
                    return self._session.get(
                        url,
                        impersonate="chrome",
                        params=params,
                        headers=merged,
                        timeout=timeout or self.timeout,
                    )
        return self._session.get(url, **kwargs)
