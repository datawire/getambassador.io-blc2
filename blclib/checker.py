from http.client import HTTPMessage
from queue import Queue
from typing import Dict, Iterable, NamedTuple, Optional, Set, Union
from urllib.parse import urldefrag, urljoin, urlparse

import bs4.element
import requests
from bs4 import BeautifulSoup

from .data_uri import DataAdapter
from .httpcache import HTTPClient


class LinkURL:
    base: Optional['LinkURL']
    ref: str
    _resolved: Optional[str]

    @property
    def resolved(self) -> str:
        if self._resolved:
            return self._resolved
        if urlparse(self.ref).scheme:
            return self.ref
        if not self.base:
            raise Exception(f"could not resolve URL: {self.ref}: is relative, and have no base for it to be relative to")
        ret = urljoin(self.base.resolved, self.ref)
        if not urlparse(ret).scheme:
            raise Exception(f"could not resolve URL: {ret}")
        return ret

    def __init__(self, ref: str, base: Optional['LinkURL'] = None, resolved: Optional[str] = None ):
        self.ref = ref
        self.base = base
        self._resolved = resolved

    def parse(self, ref: str) -> 'LinkURL':
        return LinkURL(ref, base=self)

    def __repr__(self) -> str:
        parts = [f'ref={self.ref}']
        if self.base:
            parts += [f'base={self.base}']
        if self._resolved:
            parts += [f'resolved={self._resolved}']
        return f'LinkURL({", ".join(parts)})'

class BaseLinkResult(NamedTuple):
    linkurl: LinkURL
    broken: Optional[str]


class LinkResult(NamedTuple):
    linkurl: LinkURL
    broken: Optional[str]
    pageurl: LinkURL
    html: bs4.element.Tag


def get_content_type(resp: requests.Response) -> str:
    msg = HTTPMessage()
    msg['content-type'] = resp.headers.get('content-type', None)
    return msg.get_content_type()


class BaseChecker:

    _client = HTTPClient()
    _bodycache: Dict[str, Union[BeautifulSoup, str]] = dict()
    _queue: 'Queue[str]' = Queue()
    _done: Set[str] = set()

    def __init__(self):
        self._client.mount('data:', DataAdapter())

    def enqueue(self, url: str) -> None:
        url = urldefrag(url).url
        self._queue.put(url)

    def run(self) -> None:
        while not self._queue.empty():
            self.check_page(self._queue.get())

    def get_resp(self, url) -> Union[requests.Response, str]:
        resp: Union[requests.Response, str] = "HTTP_unknown"
        try:
            resp = self._client.get(url)
            if resp.status_code != 200:
                resp = f"HTTP_{resp.status_code}"
        except BaseException as err:
            resp = f"{err}"
        return resp

    def get_soup(self, url) -> Union[BeautifulSoup, str]:
        """returns a BeautifulSoup on success, or an error string on failure."""
        baseurl = urldefrag(url).url
        if baseurl not in self._bodycache:
            soup: Union[BeautifulSoup, str] = "HTML_unknown"

            resp = self.get_resp(url)
            if isinstance(resp, str):
                soup = resp
            else:
                content_type = get_content_type(resp)
                if content_type == 'text/html':
                    try:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                    except BaseException as err:
                        soup = f"{err}"
                else:
                    soup = f"unknown Content-Type: {content_type}"

            self._bodycache[baseurl] = soup
        return self._bodycache[baseurl]

    def is_url_broken(self, url: LinkURL) -> BaseLinkResult:
        resp = self._client.get(url.resolved)
        if isinstance(resp, str):
            return BaseLinkResult(linkurl=url, broken=resp)
        url = LinkURL(ref=url.ref, base=url.base, resolved=resp.url)

        fragment = urldefrag(url.resolved).fragment
        if fragment:
            soup = self.get_soup(url.resolved)
            if isinstance(soup, str):
                return BaseLinkResult(linkurl=url, broken=f"fragment: {soup}")
            if not soup.find(id=fragment):
                return BaseLinkResult(linkurl=url, broken=f"fragment: no element with that id")

        return BaseLinkResult(linkurl=url, broken=None)

    def check_html(
        self,
        page_url: LinkURL,
        page_soup: BeautifulSoup,
    ) -> Iterable[LinkResult]:
        selectors = {
            '*': {'itemtype'},
            'a': {'href', 'ping'},
            'applet': {'archive', 'code', 'codebase', 'object', 'src'},
            'area': {'href', 'ping'},
            'audio': {'src'},
            'blockquote': {'cite'},
            'body': {'background'},
            'button': {'formaction'},
            'del': {'cite'},
            'embed': {'src'},
            'form': {'action'},
            'frame': {'longdesc', 'src'},
            'head': {'profile'},
            'html': {'manifest'},
            'iframe': {'longdesc', 'src'},
            'img': {'longdesc', 'src', 'srcset'},
            'input': {'formaction', 'src'},
            'ins': {'cite'},
            'link': {'href'},
            'menuitem': {'icon'},
            'meta': {'content'},
            'object': {'codebase', 'data'},
            'q': {'cite'},
            'script': {'src'},
            'source': {'src', 'srcset'},
            'table': {'background'},
            'tbody': {'background'},
            'td': {'background'},
            'tfoot': {'background'},
            'th': {'background'},
            'thead': {'background'},
            'tr': {'background'},
            'track': {'src'},
            'video': {'poster', 'src'},
        }

        base_url = page_url
        base_tags = page_soup.select('base[href]')
        if base_tags:
            base_url = base_url.parse(base_tags[0]['href'])

        for tagname, attrs in selectors.items():
            for attr in attrs:
                for element in page_soup.select(f"{tagname}[{attr}]"):
                    link_url = base_url.parse(element[attr])
                    inner_result = self.is_url_broken(link_url)
                    yield LinkResult(
                        linkurl=inner_result.linkurl,
                        broken=inner_result.broken,
                        pageurl=page_url,
                        html=element,
                    )

    def check_page(self, url: str) -> None:
        # Log that we're starting
        if url in self._done:
            return
        self.handle_page_starting(url)

        # Resolve any redirects
        resp = self.get_resp(url)
        if isinstance(resp, str):
            self.handle_page_error(url, resp)
            return
        page_url = LinkURL(ref=url, resolved=resp.url)
        if urldefrag(page_url.resolved).url in self._done:
            return

        # Parse the page
        soup = self.get_soup(url)
        if isinstance(soup, str):
            self.handle_page_error(url, soup)
            return
        
        # Inspect the page for bad links
        for link in self.check_html(url, soup):
            self.handle_link_result(link)

    def handle_page_starting(self, url: str) -> None:
        """handle_page_starting is called when we start processing an HTML
        page; before we fetch that page (unless it's already cached
        from a previous link check) and before any links on that page
        are handled.

        """
        pass

    def handle_link_result(self, result: LinkResult) -> None:
        """handle_link_result is called for each link found in a page.

        Using a Python-ish pseudo-code notation to express the
        structure and semantics of the result:

            class LinkResult(NamedTuple):
                linkurl: class LinkURL(NamedTuple):
                    base:     Optional[LinkURL]  # Probably the same URL as pageurl below, but possibly different if <base href> (in which case result.linkurl.base.base is the original pageurl)
                    ref:      str                # The original form of the URL reference (e.g. 'href') from the page being checked
                    resolved: str                # 'ref', but resolved to be an absolute URL; both by combining it with 'base', and by following any redirects
                pageurl: NamedTuple:         # The absolute URL of the page that this link was found on
                    ref:      str                # The original request URL
                    resolved: str                # 'ref', but after following any redirects 
                html:    bs4.element.Tag     # The HTML tag that contained the link
                broken:  Optional[str]       # Why the link is broken (or None if it isn't broken)
        """
        pass

    def handle_page_error(self, url: str, err: str) -> None:
        """handle_page_error is called whenever we encounter an error
        proccessing a page that we've been told to check for broken
        links on.  This could be because we failed to fetch the page,
        or it could be because of an HTML-parsing error.

        """
        pass
