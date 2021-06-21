#!/usr/bin/env python3
import re
import sys
from typing import Optional, Sequence
from urllib.parse import urldefrag, urlparse

from blclib import BaseChecker, Link, URLReference


def is_doc_url(url: URLReference) -> Optional[str]:
    """Returns the docs version if 'url' is a docs-url, or None if 'url' is not a docs-url."""
    parsed = urlparse(url.resolved)
    if parsed.path.startswith('/docs/') or parsed.path == '/docs':
        parts = parsed.path.split('/', 3)
        if len(parts) >= 3:
            return parts[2]
        return 'latest'
    return None


def urlpath(url: str) -> str:
    return urlparse(url).path


class Checker(BaseChecker):
    domain: str

    stats_requests: int = 0
    stats_pages: int = 0
    stats_errors: int = 0
    stats_links_total: int = 0
    stats_links_bad: int = 0
    stats_sleep: int = 0

    def __init__(self, domain: str) -> None:
        self.domain = domain
        super().__init__()

    def log_broken(self, link: Link, reason: str) -> None:
        self.stats_links_bad += 1
        msg = f'Page {link.pageurl.resolved} has a broken link: "{link.linkurl.ref}" ({reason})'
        print(msg)

    def log_ugly(self, link: Link, reason: str, suggestion: Optional[str] = None) -> None:
        self.stats_links_bad += 1
        msg = f'Page {link.pageurl.resolved} has an ugly link: "{link.linkurl.ref}" {reason}'
        if suggestion:
            msg += f' (did you mean "{suggestion}"?)'
        print(msg)

    def handle_request_starting(self, url: str) -> None:
        if not url.startswith('data:'):
            print(f"GET {urldefrag(url).url}")
            self.stats_requests += 1

    def handle_page_starting(self, url: str) -> None:
        self.stats_pages += 1

    def handle_page_error(self, url: str, err: str) -> None:
        self.stats_errors += 1
        print(f"error: {url}: {err}")

    def handle_backoff(self, url: str, secs: int) -> None:
        self.stats_sleep += secs
        print(f"backoff: {url}: retrying after {secs} seconds")

    def is_internal_domain(self, netloc: str) -> bool:
        if netloc == 'blog.getambassador.io':
            return False
        if netloc == 'getambassador.io':
            return True
        if netloc.endswith('.getambassador.io'):
            return True
        if netloc == self.domain:
            return True
        return False

    def handle_link_result(self, link: Link, broken: Optional[str]) -> None:
        self.stats_links_total += 1
        if broken:
            hostname = urlparse(link.linkurl.resolved).hostname
            netloc = urlparse(link.linkurl.resolved).netloc
            if (
                hostname
                and netloc
                and (
                    hostname.endswith(".default")
                    or netloc == "localhost:8080"
                    or hostname == "verylargejavaservice"
                    or hostname == "web-app.emojivoto"
                )
            ):
                pass  # skip
            else:
                self.log_broken(link, broken)
        else:
            # Crawl.
            if urlparse(link.linkurl.resolved).netloc == self.domain:
                self.enqueue(link.linkurl)


def main(urls: Sequence[str]) -> int:
    checker = Checker(domain=urlparse(urls[0]).netloc)
    for url in urls:
        checker.enqueue(URLReference(ref=url))
    checker.run()
    print("Summary:")
    print(
        f"  Actions: Sent {checker.stats_requests} HTTP requests and slept for {checker.stats_sleep} seconds in order to check {checker.stats_links_total} links on {checker.stats_pages} pages"
    )
    print(
        f"  Results: Encountered {checker.stats_errors} errors and {checker.stats_links_bad} bad links"
    )
    return 1 if (checker.stats_errors + checker.stats_links_bad) > 0 else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt as err:
        print(err, file=sys.stderr)
        sys.exit(130)
