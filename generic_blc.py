#!/usr/bin/env python3
import os.path
import subprocess
import sys
import threading
from typing import Optional, Protocol, Set
from urllib.parse import urldefrag, urlparse

from blclib import BaseChecker, Link, RetryAfterException, URLReference


class GenericChecker(BaseChecker):
    domain: str

    stats_requests: int = 0
    stats_pages: int = 0
    stats_errors: int = 0
    stats_links_total: int = 0
    stats_links_bad: int = 0
    stats_sleep: float = 0

    stats_sitemap: Set[str] = set()

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
        urlobj = urlparse(url)
        if urlobj.netloc == self.domain:
            self.stats_sitemap.add(urlobj.path)
        if urlobj.scheme != 'data':
            print(f"clt GET {urldefrag(url).url}")
            self.stats_requests += 1

    def handle_page_starting(self, url: str) -> None:
        self.stats_pages += 1

    def handle_page_error(self, url: str, err: str) -> None:
        self.stats_errors += 1
        print(f"error: {url}: {err}")

    def handle_429(self, err: RetryAfterException) -> None:
        print(f"backoff: {err.url}: retrying after {err.retry_after} seconds")

    def handle_sleep(self, secs: float) -> None:
        self.stats_sleep += secs
        print(f"backoff: sleeping for {secs} seconds")

    def is_internal_domain(self, netloc: str) -> bool:
        if netloc == 'telepresence.io':
            return True
        if netloc.endswith('.telepresence.io'):
            return True
        if netloc == self.domain:
            return True
        return False

    def product_should_skip_link(self, link: Link) -> bool:
        """product_should_skip_link is an overridable hook for product-specific broken link
        checkers.

        """
        return False

    def handle_link(self, link: Link) -> None:
        if not self.product_should_skip_link(link):
            # Check if this link is broken.
            self.enqueue(link)

    def product_should_skip_link_result(self, link: Link, broken: str) -> bool:
        """product_should_skip_link_result is an overridable hook for product-specific broken link
        checkers.

        """
        return False

    def product_ugly_check(self, link: Link) -> None:
        """product_ugly_check is an opportunity for product-specific broken link checkers to check
        whether a link is "ugly"; that is to check whether link is semantically-broken even
        though it is not-technically-broken.

        """
        pass

    def handle_link_result(self, link: Link, broken: Optional[str]) -> None:
        self.stats_links_total += 1
        if broken:
            if not self.product_should_skip_link_result(link, broken):
                self.log_broken(link, broken)
        else:
            # Check for "ugly" (semantically-broken, but not-technically-broken) links.
            self.product_ugly_check(link)
            # Crawl.
            if urlparse(link.linkurl.resolved).netloc == self.domain:
                # Check the linked page for broken links.
                self.enqueue(link.linkurl)


class CheckerInterface(Protocol):
    def __call__(self, domain: str) -> GenericChecker:
        ...


def crawl_filesystem(pubdir: str) -> Set[str]:
    pubdir = os.path.normpath(pubdir)
    ret: Set[str] = set()
    for root, dirs, files in os.walk(pubdir):
        for file in files:
            fullpath = os.path.join(root, file)
            urlpath = fullpath[len(pubdir) :]
            if urlpath.endswith('/index.html'):
                urlpath = urlpath[: -len('index.html')]
            ret.add(urlpath)
    return ret


def main(checkerCls: CheckerInterface, projdir: str) -> int:
    urls = [
        'http://localhost:9000/',
        'http://localhost:9000/404.html',
        'http://localhost:9000/404/',
    ]
    checker = checkerCls(domain=urlparse(urls[0]).netloc)
    for url in urls:
        checker.enqueue(URLReference(ref=url))

    with subprocess.Popen(
        [os.path.join(os.path.dirname(__file__), 'serve.js')],
        cwd=projdir,
        stdout=subprocess.PIPE,
    ) as srv:
        try:
            # Wait for the server to be ready
            assert srv.stdout
            sys.stdout.write(srv.stdout.readline().decode('utf-8'))

            # Pump the servers logs
            def pump():
                while line := srv.stdout.readline():
                    sys.stdout.write(line.decode('utf-8'))

            threading.Thread(target=pump).start()

            # Run the checker
            checker.run()
        finally:
            srv.kill()

    sitemap = crawl_filesystem(os.path.join(projdir, 'public'))
    stats_unreachable = len(sitemap - checker.stats_sitemap)
    for path in sorted(sitemap - checker.stats_sitemap):
        print(
            f'Page http://localhost:9000{path} is not reachable from elsewhere on the site'
        )

    # Print a summary
    print("Summary:")
    print(
        f"  Actions: Sent {checker.stats_requests} HTTP requests and slept for {checker.stats_sleep} seconds in order to check {checker.stats_links_total} links on {checker.stats_pages} pages."
    )
    print(
        f"  Results: Encountered {checker.stats_errors} errors, {checker.stats_links_bad} bad links, and identified {stats_unreachable} unreachable pages."
    )
    total_problems = checker.stats_errors + checker.stats_links_bad + stats_unreachable
    return 1 if total_problems > 0 else 0


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print(f"Usage: {sys.argv[0]} PROJDIR", file=sys.stderr)
            sys.exit(2)
        sys.exit(main(GenericChecker, sys.argv[1]))
    except KeyboardInterrupt as err:
        print(err, file=sys.stderr)
        sys.exit(130)
