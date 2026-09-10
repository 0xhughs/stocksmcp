"""HTTP helpers: host allowlist, redirect policy, pacing, retries."""

from __future__ import annotations

import gzip
import time
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from saudi_exchange_reports.errors import BlockedAccess, DisallowedRedirect, DownloadFailed

ALLOWED_HOSTS = frozenset({"www.saudiexchange.sa", "saudiexchange.sa"})
DEFAULT_USER_AGENT = (
    "SaudiExchangeReports/0.1 (+local research; slice-01 original-PDF retrieval)"
)


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)
    url: str = ""
    error: str | None = None


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> HttpResponse: ...


def host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_HOSTS


def assert_allowed_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DisallowedRedirect(f"Refusing non-http URL: {url}")
    if not host_allowed(url):
        raise DisallowedRedirect(f"Refusing host {parsed.hostname!r} for {url}")
    if parsed.scheme == "javascript":
        raise DisallowedRedirect("Refusing javascript URL")


class Pacing:
    def __init__(self, min_interval_seconds: float = 1.0) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last = 0.0

    def wait(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        now = time.monotonic()
        delay = self.min_interval_seconds - (now - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


def _maybe_gunzip(data: bytes) -> bytes:
    if data.startswith(b"\x1f\x8b"):
        try:
            return gzip.decompress(data)
        except OSError:
            return data
    return data


class UrllibTransport:
    """Stdlib HTTP client. Follows redirects only onto allowed hosts."""

    def __init__(self, *, timeout: float = 120.0, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.cookie_jar = CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> HttpResponse:
        assert_allowed_url(url)
        hdrs = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if headers:
            hdrs.update(headers)
        current = url
        for _ in range(5):
            assert_allowed_url(current)
            req = Request(current, method=method, headers=hdrs)
            try:
                with self._opener.open(req, timeout=timeout or self.timeout) as resp:
                    data = resp.read(max_bytes) if max_bytes else resp.read()
                    data = _maybe_gunzip(data)
                    final = resp.geturl()
                    if not host_allowed(final):
                        raise DisallowedRedirect(f"Redirected to disallowed host: {final}")
                    return HttpResponse(
                        status=getattr(resp, "status", 200) or 200,
                        body=data,
                        headers={k: v for k, v in resp.headers.items()},
                        url=final,
                    )
            except HTTPError as exc:
                location = exc.headers.get("Location") if exc.headers else None
                if exc.code in {301, 302, 303, 307, 308} and location:
                    nxt = urljoin(current, location)
                    if not host_allowed(nxt):
                        raise DisallowedRedirect(
                            f"Refusing redirect from {current} to {nxt}"
                        ) from exc
                    current = nxt
                    continue
                body = exc.read() if exc.fp else b""
                body = _maybe_gunzip(body)
                return HttpResponse(
                    status=exc.code,
                    body=body,
                    headers={k: v for k, v in (exc.headers.items() if exc.headers else [])},
                    url=current,
                )
            except URLError as exc:
                raise DownloadFailed(str(exc.reason or exc)) from exc
        raise DisallowedRedirect(f"Too many redirects for {url}")


RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def get_with_retries(
    transport: Transport,
    url: str,
    *,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
    pacing: Pacing | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> HttpResponse:
    assert_allowed_url(url)
    last: HttpResponse | None = None
    attempts = max(1, max_retries)
    for attempt in range(attempts):
        if pacing:
            pacing.wait()
        last = transport.request("GET", url, headers=headers, timeout=timeout)
        if last.error:
            raise DownloadFailed(last.error)
        if last.status in {301, 302, 303, 307, 308}:
            location = last.headers.get("Location") or last.headers.get("location")
            if not location:
                raise DisallowedRedirect("Redirect without Location")
            nxt = urljoin(url, location)
            if not host_allowed(nxt):
                raise DisallowedRedirect(f"Refusing redirect from {url} to {nxt}")
            # Allowed redirect: follow once through the same retry policy.
            url = nxt
            continue
        if last.status in RETRYABLE_STATUS and attempt + 1 < attempts:
            if retry_backoff_seconds:
                time.sleep(retry_backoff_seconds * (2**attempt))
            continue
        return last
    assert last is not None
    return last
