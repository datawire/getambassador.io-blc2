#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import threading
from typing import Dict, List, Optional
from urllib.parse import urldefrag, urlparse

from blclib import Link, URLReference
from generic_blc import CheckerInterface, GenericChecker
from utils.read_input_pages import ReadInputPages


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


def domains_manually_checked(link: Link) -> bool:
    links_to_check_manually = ["https://artifacthub.io/", "https://twitter.com"]
    return (
        len(
            [
                True
                for domain_to_skip in links_to_check_manually
                if domain_to_skip in link.linkurl.ref
            ]
        )
        > 0
    )


def link_manually_checked(link: Link) -> bool:
    """
    Validate if the link to check should be validated manually. The manual check is used when
    the external link has problem with our user agent.
    """
    links_to_check_manually = [
        "https://java.com/en/download/",
        "https://java.com/en/download/help/download_options.html",
        "https://www.comparably.com/awards/winners/best-company-boston-2022",
        "https://www.comparably.com/news/best-work-life-balance-2021/",
        "https://www.comparably.com/news/best-ceos-2021/",
        "https://www.comparably.com/news/best-leadership-teams-2021/",
        "https://www.comparably.com/news/best-companies-for-career-growth-2021/",
        "https://www.comparably.com/",
        "https://comparably.com/",
        "https://artifacthub.io/",
        "https://artifacthub.io/packages/helm/datawire/edge-stack/7.4.0#configuration",
    ]
    return (
        len(
            [
                True
                for link_to_skip in links_to_check_manually
                if link.linkurl.ref in link_to_skip
            ]
        )
        > 0
    )


class AmbassadorChecker(GenericChecker):
    _user_agent_for_link: Dict[str, str] = {
        "www.ticketmaster.com": "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0",
        "java.com": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        "tanzu.vmware.com": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        "help.github.com": "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0",
        "docs.github.com": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        "comparably.com": "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0",
    }

    def log_broken(self, link: Link, reason: str) -> None:
        self.stats_broken_links += 1
        msg = f'Page {urldefrag(link.pageurl.resolved).url} has a broken link: "{link.linkurl.ref}" ({reason})'
        print(msg)

    def log_ugly(self, link: Link, reason: str, suggestion: Optional[str] = None) -> None:
        self.stats_ugly_links += 1
        msg = f'Page {urldefrag(link.pageurl.resolved).url} has an ugly link: "{link.linkurl.ref}" {reason}'
        if suggestion:
            msg += f' (did you mean "{suggestion}"?)'
        print(msg)

    def is_internal_domain(self, netloc: str) -> bool:
        if netloc == 'blog.getambassador.io':
            return False
        if netloc == 'app.getambassador.io':
            return False
        if netloc == 'getambassador.io':
            return True
        if '.getambassador.io' in netloc:
            return True
        if netloc == self.domain:
            return True
        return False

    def product_should_skip_link(self, link: Link) -> bool:
        links_to_skip = [
            'http://verylargejavaservice:8080/',
            'https://blog.getambassador.io/search?q=canary',
            'https://app.datadoghq.com/apm/traces/',
            'http://web-app.emojivoto/',
            'http://web-app.emojivoto/leaderboard/',
            'http://verylargejavaservice.default:8080/color',
            'http://localhost:8080/',
            'http://localhost:8083/',
            'http://localhost:8083/leaderboard/',
            'http://verylargejavaservice.default:8080/',
            'https://www.getambassador.io/*/',
            'https://support.datawire.io',
            'http://localhost:3000/',
            'http://localhost:3000/color',
            'https://github.com/datawire/project-template/generate',
            'https://github.com/datawire/getambassador.io',
            'http://localhost:9000/docs/telepresence/latest/extension/intro/',
            '/favicons/apple-icon-57x57.png',
            '/favicons/apple-icon-60x60.png',
            '/favicons/apple-icon-72x72.png',
            '/favicons/apple-icon-76x76.png',
            '/favicons/apple-icon-114x114.png',
            '/favicons/apple-icon-120x120.png',
            '/favicons/apple-icon-144x144.png',
            '/favicons/apple-icon-152x152.png',
            '/favicons/apple-icon-180x180.png',
            '/favicons/android-icon-192x192.png',
            '/favicons/favicon-96x96.png',
            '/sitemap/sitemap-index.xml',
            '/docs/telepresence/latest/docker/extension/',
            'https://www.googletagmanager.com/ns.html?id=undefined',
            '/404/',
        ]
        return (
            len([True for link_to_skip in links_to_skip if link.linkurl.ref in link_to_skip])
            > 0
            or 'mailto' in link.linkurl.ref
        )

    def handle_link(self, link: Link) -> None:
        if not link_manually_checked(link) and not domains_manually_checked(link):
            super(AmbassadorChecker, self).handle_link(link)

    def product_should_skip_link_result(self, link: Link, broken: str) -> bool:
        return bool(
            (re.search('^HTTP_5[0-9]{2}$', broken))
            or (
                broken == 'HTTP_204'
                and (
                    link.linkurl.resolved.startswith('https://www.youtube.com/')
                    or link.linkurl.resolved.startswith('https://youtu.be/')
                )
            )
            or (
                broken == 'HTTP_999'
                and re.search('^https://.+linkedin.com', link.linkurl.resolved)
            )
            or (
                link.html
                and link.html.name == 'link'
                and link.html.attrName == 'href'
                and ('canonical' in link.html['rel'])
                and urlpath(link.linkurl.resolved) == urlpath(link.pageurl.resolved)
            )
        )

    def product_ugly_check(self, link: Link) -> None:
        # Check for "ugly" (semantically-broken, but not-technically-broken) links.
        ref = urlparse(link.linkurl.ref)
        if (
            link.html and (link.html.name == 'link') and ('canonical' in link.html['rel'])
        ):  # canonical links
            if ref.netloc != 'www.getambassador.io':
                # It is important that the canonical links point at the production
                # domain, so that Netlify deploy previews don't devalue the real version.
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
            # (this way, they work in Netlify previews)
            self.log_ugly(
                link=link,
                reason='is an internal link but has a domain',
                suggestion=(
                    urlparse(link.linkurl.resolved)._replace(scheme='', netloc='').geturl()
                ),
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

    @staticmethod
    def _parse_srcset_value(attrvalue: str) -> List:
        if attrvalue is None or attrvalue == "":
            return []

        if (
            "?rect=" in attrvalue or "&rect=" in attrvalue
        ) and "https://cdn.sanity.io/images/" in attrvalue:
            return re.findall("https[^ ]*", attrvalue)

        return [desc.split()[0] for desc in attrvalue.split(',')]


def main(
    checkerCls: CheckerInterface, projdir: str, pages_to_check_file: str, base_address: str
) -> int:
    urls = [
        f'{base_address}/',
        f'{base_address}/404.html',
        f'{base_address}/404/',
    ]
    checker = checkerCls(domain=urlparse(urls[0]).netloc)

    if len(pages_to_check_file) > 0:
        pages_to_check_reader = ReadInputPages(pages_to_check_file, f'{base_address}/')
        pages_to_check = pages_to_check_reader.read_input_pages()
        checker.pages_to_check = pages_to_check
        urls = urls if len(pages_to_check) == 0 else pages_to_check

    for url in urls:
        checker.enqueue(URLReference(ref=url))

    with subprocess.Popen(
        [os.path.join(os.path.abspath(os.path.dirname(__file__)), 'serve.js')],
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

    # Print a summary
    print("Summary:")
    print(
        f"  Actions: Sent {checker.stats_requests} HTTP requests and slept for {checker.stats_sleep} seconds in order to check {checker.stats_links_total} links on {checker.stats_pages} pages."
    )
    print(
        f"  Results: Encountered {checker.stats_broken_links} errors, {checker.stats_links_bad} bad links."
    )
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) < 4:
            print(
                f"Usage: {sys.argv[0]} PROJDIR PAGES_TO_CHECK BASE_ADDRESS", file=sys.stderr
            )
            sys.exit(2)
        sys.exit(
            main(
                AmbassadorChecker,
                sys.argv[1],
                sys.argv[2],
                sys.argv[3],
            )
        )
    except KeyboardInterrupt as err:
        print(err, file=sys.stderr)
        sys.exit(130)
