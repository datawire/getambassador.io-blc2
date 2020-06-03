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
    original: str

    @property
    def resolved(self) -> str:
        if urlparse(self.original).scheme:
            return self.original
        if not self.base:
            raise Exception(
                f"could not resolve to an absolute URL: {self.original}")
        ret = urljoin(self.base.resolved, self.original)
        if not urlparse(ret).scheme:
            raise Exception(f"could not resolve to an absolute URL: {ret}")
        return ret

    def __init__(self, ref: str, base: Optional['LinkURL'] = None):
        self.original = ref
        self.base = base

    def parse(self, ref: str) -> 'LinkURL':
        return LinkURL(ref, base=self)


class LinkResult(NamedTuple):
    url: LinkURL
    html: bs4.element.Tag
    broken: bool
    broken_reason: Optional[str]


def get_content_type(resp: requests.Response) -> str:
    msg = HTTPMessage()
    msg['content-type'] = resp.headers.get('content-type', None)
    return msg.get_content_type()


class Checker:

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
            url = self._queue.get()
            if url not in self._done:
                self.check_page(url)

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

    def is_url_broken(self, url: str) -> Optional[str]:
        resp = self._client.get(url)
        if isinstance(resp, str):
            return resp

        baseurl, fragment = urldefrag(url)
        if fragment:
            soup = self.get_soup(url)
            if isinstance(soup, str):
                return f"fragment: {soup}"
            if not soup.find(id=fragment):
                return f"fragment: no element with that id"

        return None

    def check_html(
        self,
        page_url: str,
        page_soup: BeautifulSoup,
    ) -> Iterable[LinkResult]:
        baseurl = LinkURL(page_url)
        basetags = page_soup.select('base[href]')
        if basetags:
            baseurl = baseurl.parse(basetags[0]['href'])

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

        for tagname, attrs in selectors.items():
            for attr in attrs:
                for element in page_soup.select(f"{tagname}[{attr}]"):
                    link_url = baseurl.parse(element[attr])
                    broken_reason = self.is_url_broken(link_url.resolved)
                    yield LinkResult(
                        url=link_url,
                        html=element,
                        broken=bool(broken_reason),
                        broken_reason=broken_reason,
                    )

    def check_page(self, url: str) -> None:
        soup = self.get_soup(url)
        if isinstance(soup, str):
            print(f"error: {soup}")
            return
        for link in self.check_html(url, soup):
            print(f"link: {link}")
