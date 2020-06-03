import re
import sys
from typing import Iterable, Optional
from urllib.parse import urlparse
from blclib import BaseChecker, LinkResult

def log_broken(result: LinkResult) -> None:
    print(f'Page {result.pageurl.resolved} has a broken link: "{result.linkurl.ref}" ({result.broken})')    

def log_ugly(result: LinkResult, reason: str, suggestion: Optional[str]) -> None:
    msg = f'Page {result.pageurl.resolved} has an ugly link: "{result.linkurl.ref}" {reason}'
    if suggestion:
        msg += f' (did you mean "{suggestion}"?)'
    print(msg)

def is_doc_url(url: str) -> Optional[str]:
    """Returns the docs version if 'url' is a docs-url, or None if 'url' is not a docs-url."""
    parsed = urlparse(url)
    if parsed.path.startswith('/docs/') or parse.path == '/docs':
        parts = parsed.path.split('/', 3)
        if len(parts) >= 3:
            return parts[2]
        return 'latest'
    return None

class Checker(BaseChecker):
    domain: str

    def __init__(self, domain: str):
        self.domain = domain
    
    def handle_page_starting(self, url: str) -> None:
        print(f"Processing {url}")

    def handle_page_error(self, url: str, err: str) -> None:
        print(f"error: {url}: {err}")

    def handle_link_result(self, result: LinkResult) -> None:
        if result.broken:
            # Handle broken links
            if ((result.linkurl.ref == 'https://blog.getambassador.io/search?q=canary') or
                (result.linkurl.ref == 'https://app.datadoghq.com/apm/traces') or
                (re.match('^HTTP_5[0-9]{2}$', result.broken)) or
                (result.broken == 'HTTP_204' and (result.linkurl.resolved.startswith('https://www.youtube.com/') or result.linkurl.resolved.startswith('https://youtu.be/'))) or
                (result.broken == 'HTTP_429') or
                (result.broken == 'HTTP_999' and result.linkurl.resolved.startswith('https://www.linkedin.com/')) or
                (result.html.tagName == 'link' and result.html.attrName == 'href' and result.html['rel'] == 'canonical' and urlparse(result.linkurl.resolved).path == urlparse(result.pageurl.resolved).path) or
                (result.html.text == 'Edit this page on GitHub')
            ):
                pass  # skip
            else:
                log_broken(result)
        else:
            # Crawl.
            if urlparse(result.linkurl.resolved).netloc == self.domain:
                self.enqueue(result.linkurl.resolved)
            # Check for "ugly" (semantically-broken, but not-technically-broken) links.
            ref = urlparse(result.linkurl.ref)
            if result.html.tagName == 'link' and result.html['rel'] == 'canonical': # canonical links
                if ref.netloc != 'www.getambassador.io':
                    log_ugly(result=result,
                             reason='is a canonical but does not point at www.getambassador.io',
                             suggestion=urlparse(result.linkurl.resolved)._replace(scheme='https', netloc='www.getambassador.io').geturl())
                # Other than that, the canonicals don't need to be inspected more, because they're
                # allowed (expected!) to be cross-version.
            elif re.match(r'^(.*\.)?getambassador.io$', ref.netloc) or ref.netloc == domain: # should-be-internal links
                # Links within getambassador.io should not mention the scheme or domain
                # (this way, they work in netlify previews)
                log_ugly(result=result,
                         reason='is an internal link but has a domain',
                         suggestion=urlparse(result.linkurl.resolved)._replace(scheme='', netloc='').geturl())
            elif not ref.netloc: # internal links
                src_ver = is_docs_url(result.pageurl.resolved)
                dst_ver = is_docs_url(result.linkurl.resolved)
                if src_ver and dst_ver and (dst_ver != src_ver):
                    # Mismatched docs versions
                    log_ugly(result=result,
                             reason=f'is a link from docs version={src_ver} to docs version={dst_ver}')

def main(urls: Iterable[str]) -> None:
    checker = Checker()
    for url in urls:
        checker.enqueue(url)
    checker.run()


if __name__ == "__main__":
    main(sys.argv[1:])
