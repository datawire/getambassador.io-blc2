#!/usr/bin/env python3
import re
import sys
from typing import Optional, Sequence
from urllib.parse import urlparse

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
            self.stats_requests += 1
            print(f"GET {url}")

    def handle_page_starting(self, url: str) -> None:
        self.stats_pages += 1
        print(f"Processing {url}")

    def handle_page_error(self, url: str, err: str) -> None:
        self.stats_errors += 1
        print(f"error: {url}: {err}")

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
            # Handle broken links
            if (
                (link.linkurl.ref == 'https://blog.getambassador.io/search?q=canary')
                or (link.linkurl.ref == 'https://app.datadoghq.com/apm/traces')
                or (re.match('^HTTP_5[0-9]{2}$', broken))
                or (
                    broken == 'HTTP_204'
                    and (
                        link.linkurl.resolved.startswith('https://www.youtube.com/')
                        or link.linkurl.resolved.startswith('https://youtu.be/')
                    )
                )
                or (broken == 'HTTP_429')
                or (
                    broken == 'HTTP_999'
                    and link.linkurl.resolved.startswith('https://www.linkedin.com/')
                )
                or (
                    link.html.tagName == 'link'
                    and link.html.attrName == 'href'
                    and link.html['rel'] == 'canonical'
                    and urlpath(link.linkurl.resolved) == urlpath(link.pageurl.resolved)
                )
                or (link.html.text == 'Edit this page on GitHub')
            ):
                pass  # skip
            else:
                self.log_broken(link, broken)
        else:
            # Check for "ugly" (semantically-broken, but not-technically-broken) links.
            ref = urlparse(link.linkurl.ref)
            if (
                link.html.tagName == 'link' and link.html['rel'] == 'canonical'
            ):  # canonical links
                if ref.netloc != 'www.getambassador.io':
                    self.log_ugly(
                        link=link,
                        reason='is a canonical but does not point at www.getambassador.io',
                        suggestion=urlparse(link.linkurl.resolved)
                        ._replace(scheme='https', netloc='www.getambassador.io')
                        .geturl(),
                    )
                # Other than that, the canonicals don't need to be inspected more, because they're
                # allowed (expected!) to be cross-version.
            elif self.is_internal_domain(ref.netloc):  # should-be-internal links
                # Links within getambassador.io should not mention the scheme or domain
                # (this way, they work in netlify previews)
                self.log_ugly(
                    link=link,
                    reason='is an internal link but has a domain',
                    suggestion=urlparse(link.linkurl.resolved)
                    ._replace(scheme='', netloc='')
                    .geturl(),
                )
            elif not ref.netloc:  # internal links
                src_ver = is_doc_url(link.pageurl)
                dst_ver = is_doc_url(link.linkurl)
                if src_ver and dst_ver and (dst_ver != src_ver):
                    # Mismatched docs versions
                    self.log_ugly(
                        link=link,
                        reason=f'is a link from docs version={src_ver} to docs version={dst_ver}',
                    )
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
        f"  Actions: Sent {checker.stats_requests} HTTP requests in order to check {checker.stats_links_total} links on {checker.stats_pages} pages"
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
