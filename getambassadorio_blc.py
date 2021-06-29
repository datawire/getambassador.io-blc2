#!/usr/bin/env python3
import re
import sys
from typing import Optional
from urllib.parse import urlparse

from blclib import Link, URLReference
from generic_blc import GenericChecker, main


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


class AmbassadorChecker(GenericChecker):
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

    def product_should_skip_link(self, link: Link) -> bool:
        return (link.linkurl.ref == 'https://blog.getambassador.io/search?q=canary') or (
            link.linkurl.ref == 'https://app.datadoghq.com/apm/traces'
        )

    def product_should_skip_link_result(self, link: Link, broken: str) -> bool:
        return bool(
            (re.match('^HTTP_5[0-9]{2}$', broken))
            or (
                broken == 'HTTP_204'
                and (
                    link.linkurl.resolved.startswith('https://www.youtube.com/')
                    or link.linkurl.resolved.startswith('https://youtu.be/')
                )
            )
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
        )

    def product_ugly_check(self, link: Link) -> None:
        # Check for "ugly" (semantically-broken, but not-technically-broken) links.
        ref = urlparse(link.linkurl.ref)
        if (
            link.html.tagName == 'link' and link.html['rel'] == 'canonical'
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


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print(f"Usage: {sys.argv[0]} PROJDIR", file=sys.stderr)
            sys.exit(2)
        sys.exit(main(AmbassadorChecker, sys.argv[1]))
    except KeyboardInterrupt as err:
        print(err, file=sys.stderr)
        sys.exit(130)
