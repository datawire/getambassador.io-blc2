import re
import sys
from typing import Iterable, Optional
from urllib.parse import urlparse
from blclib import BaseChecker, LinkResult

def log_broken(result: LinkResult) -> None:
    print(f'Page {result.pageurl.resolved} has a broken link: "{result.url.original}" ({result.broken_reason})')    

def log_ugly(result: LinkResult, reason: str, suggestion: Optional[str]) -> None:
    msg = f'Page {result.pageurl.resolved} has an ugly link: "{result.url.original}" {reason}'
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
    
    def handle_link_result(self, result: LinkResult) -> None:
        if result.broken:
            # Handle broken links
            assert result.broken_reason
            if result.url.original == 'https://blog.getambassador.io/search?q=canary':
                pass  # skip
            elif result.url.original == 'https://app.datadoghq.com/apm/traces':
                pass  # skip
            elif re.match('^HTTP_5[0-9]{2}$', result.broken_reason):
                pass  # skip
            elif result.broken_reason == 'HTTP_204' and (result.url.resolved.startswith('https://www.youtube.com/') or result.url.resolved.startswith('https://youtu.be/')):
                pass  # skip
            elif result.broken_reason == 'HTTP_429':
                pass  # skip
            elif result.broken_reason == 'HTTP_999' and result.url.resolved.startswith('https://www.linkedin.com/'):
                pass  # skip
            elif result.html.tagName == 'link' and result.html.attrName == 'href' and result.html['rel'] == 'canonical' and urlparse(result.url.resolved).path == urlparse(result.pageurl.resolved).path:
                pass  # skip
            elif result.html.text == 'Edit this page on GitHub':
                pass  # skip
            else:
                log_broken(result)
        else:
            # Crawl.
            if urlparse(result.url.resolved).netloc == self.domain:
                self.enqueue(result.url.resolved)
            # Check for "ugly" (semantically-broken, but not-technically-broken) links.
            original = urlparse(result.url.original)
            if result.html.tagName == 'link' and result.html['rel'] == 'canonical': # canonical links
                if original.netloc != 'www.getambassador.io':
                    log_ugly(result=result,
                             reason='is a canonical but does not point at www.getambassador.io',
                             suggestion=urlparse(result.url.resolved)._replace(scheme='https', netloc='www.getambassador.io').geturl())
                # Other than that, the canonicals don't need to be inspected more, because they're
                # allowed (expected!) to be cross-version.
            elif re.match(r'^(.*\.)?getambassador.io$', original.netloc) or original.netloc == domain: # should-be-internal links
                # Links within getambassador.io should not mention the scheme or domain
                # (this way, they work in netlify previews)
                log_ugly(result=result,
                         reason='is an internal link but has a domain',
                         suggestion=urlparse(result.url.resolved)._replace(scheme='', netloc='').geturl())
            elif not original.netloc: # internal links
                src_ver = is_docs_url(result.pageurl.resolved)
                dst_ver = is_docs_url(result.url.resolved)
                if src_ver and dst_ver and (dst_ver != src_ver):
                    # Mismatched docs versions
                    log_ugly(result=result,
                             reason=f'is a link from docs version={src_ver} to docs version={dst_ver}
                if src.path.startswith('/docs/') and dst.path.startswith('/docs/'):
                    # Link from docs to docs--make sure that they the versions match.
                dstIsAbsolutePath = (result.url.original == result.url.resolved) || (result.url.original + '/' == result.url.resolved) || result.url.original.startsWith('/');
                dstIsAbsoluteDomain = (result.url.original == result.url.resolved) || (result.url.original + '/' == result.url.resolved) || result.url.original.startsWith('//');
                srcIsAmbassadorDocs = ambassador_docs_dirs.includes(src.pathname.split('/')[1]);
                dstIsAmbassadorDocs = ambassador_docs_dirs.includes(dst.pathname.split('/')[1]);
                if dstIsAbsoluteDomain:
                    let suggestion = dst.pathname + dst.hash;
                    console.log(`Page {result.pageurl.resolved} has an ugly link: "{result.url.original}" has a domain (did you mean "{suggestion}"?)`);
        

def main(urls: Iterable[str]) -> None:
    checker = Checker()
    for url in urls:
        checker.enqueue(url)
    checker.run()


if __name__ == "__main__":
    main(sys.argv[1:])
