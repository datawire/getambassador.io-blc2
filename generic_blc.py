#!/usr/bin/env python3
import os.path
import re
import subprocess
import sys
import threading
import time
from typing import Optional, Protocol, Set
from urllib.parse import urldefrag, urlparse

import bs4.element
from bs4 import BeautifulSoup

from blclib import BaseChecker, Link, RetryAfterException, URLReference


class GenericChecker(BaseChecker):
    domain: str

    stats_requests: int = 0
    stats_pages: int = 0
    stats_errors: int = 0
    stats_links_total: int = 0
    stats_links_bad: int = 0
    stats_sleep: float = 0
    stats_broken_links: int = 0
    stats_ugly_links: int = 0

    stats_sitemap: Set[str] = set()

    def __init__(self, domain: str) -> None:
        self.domain = domain
        super().__init__()

    def log_broken(self, link: Link, reason: str) -> None:
        self.stats_links_bad += 1
        msg = f'Page {urldefrag(link.pageurl.resolved).url} has a broken link: "{link.linkurl.ref}" ({reason})'
        print(msg)

    def log_ugly(self, link: Link, reason: str, suggestion: Optional[str] = None) -> None:
        self.stats_links_bad += 1
        msg = f'Page {urldefrag(link.pageurl.resolved).url} has an ugly link: "{link.linkurl.ref}" {reason}'
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

    def handle_html_extra(self, page_url: URLReference, page_soup: BeautifulSoup) -> None:
        # It is important that all pages have canonicals so that Netlify previews don't
        # devalue the real site.
        def is_canonical(tag: bs4.element.Tag) -> bool:
            return (tag.name == 'link') and bool(tag['href']) and ('canonical' in tag['rel'])

        if not page_soup.find_all(is_canonical):
            print(f'Page {urldefrag(page_url.resolved).url} does not have a canonical')

    def handle_page_error(self, url: str, err: str) -> None:
        self.stats_errors += 1
        print(f"error: {url}: {err}")

    def handle_timeout(self, url: str, err: str) -> None:
        self.stats_errors += 1
        print(f"Page {url} produced a timeout error. A manual review is required")

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
            url = urlparse(link.linkurl.resolved)
            if link.linkurl.ref.endswith(".eot?#iefix"):
                link = link._replace(
                    linkurl=link.linkurl._replace(ref=link.linkurl.ref[: -len("?#iefix")])
                )
            elif (
                url.netloc == 'github.com'
                and re.search(r'^/[^/]+/[^/]+$', url.path)
                and url.fragment
                and not url.fragment.startswith('user-content-')
            ):
                link = link._replace(
                    linkurl=link.linkurl._replace(
                        resolved=url._replace(
                            fragment='user-content-' + url.fragment
                        ).geturl()
                    )
                )
            elif (
                url.netloc == 'github.com'
                and re.search(r'^/[^/]+/[^/]+/blob/', url.path)
                and re.search(r'^L[0-9]+-L[0-9]+$', url.fragment)
            ):
                self.enqueue(
                    link._replace(
                        linkurl=link.linkurl._replace(
                            resolved=url._replace(
                                fragment=url.fragment.split('-')[0]
                            ).geturl()
                        )
                    )
                )
                self.enqueue(
                    link._replace(
                        linkurl=link.linkurl._replace(
                            resolved=url._replace(
                                fragment=url.fragment.split('-')[1]
                            ).geturl()
                        )
                    )
                )
                return
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
            if urlpath == "/_redirects" or urlpath == "/_headers":
                continue
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
        [os.path.join(os.path.abspath(os.path.dirname(__file__)), 'serve.js')],
        cwd=projdir,
        stdout=subprocess.PIPE,
    ) as srv:
        try:
            server_ready = [False]
            # Wait for the server to be ready
            assert srv.stdout
            sys.stdout.write(srv.stdout.readline().decode('utf-8'))

            # Pump the servers logs
            def pump(flag):
                while line := srv.stdout.readline():
                    line = line.decode('utf-8')
                    if "Serving" in line:
                        flag[0] = True
                    sys.stdout.write(line)

            threading.Thread(target=pump, args=[server_ready]).start()

            # wait until the server is ready
            while not server_ready[0]:
                time.sleep(3)
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
