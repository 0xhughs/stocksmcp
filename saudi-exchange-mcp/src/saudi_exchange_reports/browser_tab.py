"""Browser-driven Financial Statements tab listing.

Used only when urllib website AJAX (statementsTabData) does not return the
reports table. This is public UI automation on www.saudiexchange.sa, not an
official API. Result HTML is parsed as untrusted data; PDF bytes are still
downloaded through the constrained urllib transport.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from saudi_exchange_reports.errors import DisallowedRedirect, DownloadFailed
from saudi_exchange_reports.http import assert_allowed_url, host_allowed

TAB_SELECTOR = "#finacialStatementAndReports"
FSPDF_SELECTOR = "a[href*='/Resources/fsPdf/']"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def profile_url_with_locale(profile_url: str, locale: str) -> str:
    parsed = urlparse(profile_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["locale"] = [locale]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


class PlaywrightTabRenderer:
    """Click the observed Financial Statements tab and return page HTML."""

    def __init__(self, *, timeout_ms: int = 60000, headless: bool = True) -> None:
        self.timeout_ms = timeout_ms
        self.headless = headless

    def fetch_tab_html(self, profile_url: str, *, symbol: str) -> str:
        del symbol  # Present in the tab-renderer contract; encoded in profile_url.
        assert_allowed_url(profile_url)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise DownloadFailed(
                "Playwright is not installed; cannot list reports from the "
                "browser-driven Financial Statements tab."
            ) from exc

        last_error: Exception | None = None
        delays = (0.0, 2.0, 4.0)
        for attempt, delay in enumerate(delays):
            if delay:
                import time

                time.sleep(delay)
            try:
                with sync_playwright() as playwright:
                    return self._fetch_once(playwright, profile_url)
            except (DisallowedRedirect, DownloadFailed):
                raise
            except Exception as exc:  # noqa: BLE001 — retry Access Denied / timeouts
                last_error = exc
                if attempt + 1 >= len(delays):
                    break
        raise DownloadFailed(
            f"Browser-driven Financial Statements tab listing failed: {last_error!r}"
        )

    def _fetch_once(self, playwright: object, profile_url: str) -> str:
        chromium = getattr(playwright, "chromium")
        browser = chromium.launch(
            channel="chrome",
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            context = browser.new_context(
                user_agent=CHROME_USER_AGENT,
                locale="en-US",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "*/*",
                },
            )
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)
            html_parts: list[str] = []
            errors: list[str] = []
            # English and Arabic tabs each expose one language of fsPdf icons.
            for locale in ("en", "ar"):
                target = profile_url_with_locale(profile_url, locale)
                assert_allowed_url(target)
                try:
                    html_parts.append(self._load_tab(page, target))
                except DisallowedRedirect:
                    raise
                except Exception as exc:  # noqa: BLE001 — keep the other locale
                    errors.append(f"{locale}: {exc}")
            combined = "\n".join(html_parts)
            if "/Resources/fsPdf/" not in combined:
                detail = "; ".join(errors) if errors else "no tab HTML"
                raise DownloadFailed(
                    "Browser tab HTML contained no /Resources/fsPdf/ links "
                    f"({detail})."
                )
            return combined
        finally:
            browser.close()

    def _load_tab(self, page: object, profile_url: str) -> str:
        response = page.goto(profile_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        final_url = page.url or profile_url
        if not host_allowed(final_url):
            raise DisallowedRedirect(f"Browser navigated off allowed host: {final_url}")
        title = (page.title() or "").casefold()
        if "access denied" in title:
            raise DownloadFailed(f"Browser profile GET was Access Denied for {profile_url}")
        if response is not None and response.status in {401, 403}:
            raise DownloadFailed(f"HTTP {response.status} loading profile in browser")
        tab = page.locator(TAB_SELECTOR)
        if tab.count() == 0:
            raise DownloadFailed(
                "Financial Statements tab (#finacialStatementAndReports) was not present."
            )
        tab.first.click()
        page.wait_for_selector(FSPDF_SELECTOR, timeout=self.timeout_ms)
        html = page.content()
        if "/Resources/fsPdf/" not in html:
            raise DownloadFailed("Browser tab HTML contained no /Resources/fsPdf/ links.")
        return html
