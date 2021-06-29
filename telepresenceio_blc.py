#!/usr/bin/env python3
import sys
from urllib.parse import urlparse

from blclib import Link
from generic_blc import GenericChecker, main


class TelepresenceChecker(GenericChecker):
    def is_internal_domain(self, netloc: str) -> bool:
        if netloc == 'telepresence.io':
            return True
        if netloc.endswith('.telepresence.io'):
            return True
        if netloc == self.domain:
            return True
        return False

    def product_should_skip_link(self, link: Link) -> bool:
        hostname = urlparse(link.linkurl.resolved).hostname
        netloc = urlparse(link.linkurl.resolved).netloc
        return bool(
            hostname
            and netloc
            and (
                hostname.endswith(".default")
                or netloc == "localhost:8080"
                or hostname == "verylargejavaservice"
                or hostname == "web-app.emojivoto"
            )
        )

    def product_ugly_check(self, link: Link) -> None:
        # Check for "ugly" (semantically-broken, but not-technically-broken) links.
        ref = urlparse(link.linkurl.ref)
        if (
            link.html.tagName == 'link' and link.html['rel'] == 'canonical'
        ):  # canonical links
            if ref.netloc not in ['www.getambassador.io', 'www.telepresence.io']:
                # It is important that the canonical links point at the production
                # domain, so that Netlify deploy previews don't devalue the real version.
                self.log_ugly(
                    link=link,
                    reason='is a canonical but does not point at www.getambassador.io or www.telepresence.io',
                    suggestion=(
                        urlparse(link.linkurl.resolved)
                        ._replace(scheme='https', netloc='www.telepresence.io')
                        .geturl()
                    ),
                )
        elif self.is_internal_domain(ref.netloc):  # should-be-internal links
            # Links within telepresence.io should not mention the scheme or domain
            # (this way, they work in Netlify previews)
            self.log_ugly(
                link=link,
                reason='is an internal link but has a domain',
                suggestion=urlparse(link.linkurl.resolved)
                ._replace(scheme='', netloc='')
                .geturl(),
            )


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print(f"Usage: {sys.argv[0]} PROJDIR", file=sys.stderr)
            sys.exit(2)
        sys.exit(main(TelepresenceChecker, sys.argv[1]))
    except KeyboardInterrupt as err:
        print(err, file=sys.stderr)
        sys.exit(130)
