import re
import time
from http.client import HTTPMessage
from queue import Queue
from typing import Container, Dict, List, Mapping, Optional, Set, Text, Tuple, Union
from urllib.parse import urldefrag

# import bs4.element
import requests
from bs4 import BeautifulSoup

from .data_uri import DataAdapter
from .httpcache import HTTPClient as BaseHTTPClient
from .models import Link, URLReference


def get_content_type(resp: requests.Response) -> str:
    msg = HTTPMessage()
    msg['content-type'] = resp.headers.get('content-type', None)
    return msg.get_content_type()


class HTTPClient(BaseHTTPClient):
    _checker: 'BaseChecker'

    def __init__(self, checker: 'BaseChecker'):
        self._checker = checker
        super().__init__()
        self.mount('data:', DataAdapter())

    def hook_before_send(
        self,
        request: requests.models.PreparedRequest,
        stream: bool = False,
        timeout: Union[None, float, Tuple[float, float], Tuple[float, None]] = None,
        verify: Union[bool, str] = True,
        cert: Union[None, Union[bytes, Text], Container[Union[bytes, Text]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> None:
        assert request.url
        self._checker.handle_request_starting(request.url)

    def hook_before_sleep(
        self,
        retry_after: int,
        request: requests.models.PreparedRequest,
        stream: bool = False,
        timeout: Union[None, float, Tuple[float, float], Tuple[float, None]] = None,
        verify: Union[bool, str] = True,
        cert: Union[None, Union[bytes, Text], Container[Union[bytes, Text]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> None:
        assert request.url
        self._checker.handle_backoff(request.url, retry_after)


def url_from_meta_http_equiv_refresh(input: str) -> Optional[str]:
    # https://html.spec.whatwg.org/multipage/semantics.html#attr-meta-http-equiv-refresh

    # step 1 - step 11.7
    urlString = re.sub(r"^\s*[0-9.]*\s*[;,]?\s*(?:[Uu][Rr][Ll]\s*=\s*)?", '', input)
    if urlString == input:
        return None
    # step 11.8-11.10
    if urlString.startswith('"'):
        urlString = re.sub('".*', '', urlString[1:])
    elif urlString.startswith("'"):
        urlString = re.sub("'.*", '', urlString[1:])
    return urlString


class BaseChecker:

    _client: HTTPClient
    _bodycache: Dict[str, Union[BeautifulSoup, str]] = dict()
    _queue: 'Queue[Union[Link,URLReference]]' = Queue()
    _queued_pages: Set[str] = set()
    _done_pages: Set[str] = set()

    def __init__(self) -> None:
        self._client = HTTPClient(self)

    def enqueue(self, task: Union[Link, URLReference]) -> None:
        """enqueue a task for the checker to do.
        If the task is a...

          - URLReference: Check the page pointed to by this URL for
            broken links; call handle_page_starting() and possibly
            handle_page_error(); enqueue all links found on the page.

          - Link: Check if the link is broken; then call
            handle_link_result().

        """
        if isinstance(task, URLReference):
            clean_url = urldefrag(task.resolved).url
            if (clean_url in self._done_pages) or (clean_url in self._queued_pages):
                return
            self._queued_pages.add(clean_url)
        self._queue.put(task)

    def run(self) -> None:
        """Run the checker; keep running tasks until the queue (see
        `enqueue()`) is empty.

        """
        while not self._queue.empty():
            task = self._queue.get()
            if isinstance(task, Link):
                self._check_link(task)
            elif isinstance(task, URLReference):
                self._check_page(task)
            else:
                assert False

    def _get_resp(self, url: str) -> Union[requests.Response, str]:
        try:
            resp: requests.Response = self._client.get(url)
            if resp.status_code != 200:
                reterr = f"HTTP_{resp.status_code}"
                if resp.status_code == 429 or int(resp.status_code / 100) == 5:
                    self.handle_page_error(url, reterr)
                return reterr
            return resp
        except Exception as err:
            reterr = f"{err}"
            self.handle_page_error(url, reterr)
            return reterr

    def _get_soup(self, url: str) -> Union[BeautifulSoup, str]:
        """returns a BeautifulSoup on success, or an error string on failure."""
        baseurl = urldefrag(url).url
        if baseurl not in self._bodycache:
            soup: Union[BeautifulSoup, str] = "HTML_unknown"

            resp = self._get_resp(url)
            if isinstance(resp, str):
                soup = resp
            else:
                content_type = get_content_type(resp)
                if content_type == 'text/html':
                    try:
                        soup = BeautifulSoup(resp.text, 'lxml')
                    except Exception as err:
                        soup = f"{err}"
                else:
                    soup = f"unknown Content-Type: {content_type}"

            self._bodycache[baseurl] = soup
        return self._bodycache[baseurl]

    def _check_link(self, link: Link) -> None:
        broken = self._is_link_broken(link)
        self.handle_link_result(link, broken)

    def _is_link_broken(self, link: Link) -> Optional[str]:
        # Resolve redirects
        resp = self._get_resp(link.linkurl.resolved)
        if isinstance(resp, str):
            return resp
        link = link._replace(linkurl=link.linkurl._replace(resolved=resp.url))

        # Check the fragment
        fragment = urldefrag(link.linkurl.resolved).fragment
        if fragment:
            soup = self._get_soup(link.linkurl.resolved)
            if isinstance(soup, str):
                return f"fragment: {soup}"
            if not (soup.find(id=fragment) or soup.find("a", {"name": fragment})):
                return f"fragment: no element with that id/name"

        return None

    def _process_html(self, page_url: URLReference, page_soup: BeautifulSoup) -> None:
        # This list of selectors is the union of all lists in
        # https://github.com/stevenvachon/broken-link-checker/blob/master/lib/internal/tags.js
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
            for attrname in attrs:
                for element in page_soup.select(f"{tagname}[{attrname}]"):
                    attrvalue = element[attrname]
                    url_strs: List[str] = []

                    if attrname == 'content':
                        if element.get('http-equiv', '').lower() == 'refresh':
                            # https://html.spec.whatwg.org/multipage/semantics.html#attr-meta-http-equiv-refresh
                            url = url_from_meta_http_equiv_refresh(attrvalue)
                            if url:
                                url_strs = [url]
                    elif attrname == 'ping':
                        # https://html.spec.whatwg.org/multipage/links.html#ping
                        url_strs = [attrvalue.split()]
                    elif attrname == 'srcset':
                        # https://html.spec.whatwg.org/multipage/images.html#srcset-attributes
                        url_strs = [desc.split()[0] for desc in attrvalue.split(',')]
                    else:
                        url_strs = [attrvalue]

                    for url_str in url_strs:
                        link_url = base_url.parse(url_str)
                        self.enqueue(Link(linkurl=link_url, pageurl=page_url, html=element))

    def _check_page(self, page_url: URLReference) -> None:
        # Handle redirects
        page_resp = self._get_resp(page_url.resolved)
        if isinstance(page_resp, str):
            page_clean_url = urldefrag(page_url.resolved).url
            self._done_pages.add(page_clean_url)
            self.handle_page_starting(page_clean_url)
            self.handle_page_error(page_clean_url, page_resp)
            return
        page_urls = set(urldefrag(r.url).url for r in ([page_resp] + page_resp.history))
        page_url = page_url._replace(resolved=page_resp.url)
        page_clean_url = urldefrag(page_url.resolved).url

        # Handle short-circuiting
        if page_clean_url in self._done_pages:
            return
        self._done_pages.update(page_urls)

        # Log that we're starting
        self.handle_page_starting(page_clean_url)

        # Inspect the page for bad links #################################################

        content_type = get_content_type(page_resp)
        if content_type == 'application/javascript':
            # TODO: check for ES6 imports
            pass
        elif content_type == 'application/json':
            pass  # nothing to do
        elif content_type == 'application/manifest+json':
            # TODO: https://w3c.github.io/manifest/
            pass
        elif content_type == 'image/svg+xml':
            # TODO: check SVGs for links
            pass
        elif content_type == 'application/pdf':
            # TODO: check PDFs for links
            pass
        elif content_type == 'application/x-yaml':
            pass  # nothing to do
        elif content_type == 'image/jpeg':
            pass  # nothing to do
        elif content_type == 'image/png':
            pass  # nothing to do
        elif content_type == 'text/html':
            page_soup = self._get_soup(page_clean_url)
            if isinstance(page_soup, str):
                self.handle_page_error(page_clean_url, page_soup)
                return
            self._process_html(page_url, page_soup)
        else:
            self.handle_page_error(page_clean_url, f"unknown Content-Type: {content_type}")

    def handle_request_starting(self, url: str) -> None:
        """handle_request_starting is a hook; called before we send a
        (non-cached) request.

        """
        pass

    def handle_page_starting(self, url: str) -> None:
        """handle_page_starting is a hook; called when we start processing an
        HTML page; before we fetch that page (unless it's already
        cached from a previous link check) and before any links on
        that page are handled.

        """
        pass

    def handle_link_result(self, link: Link, broken: Optional[str]) -> None:
        """handle_link_result is a hook; called for each link found in a page.

        Using a Python-ish pseudo-code notation to express the
        structure and semantics of the 'link' argument:

            class Link(NamedTuple):
                linkurl: class URLReference(NamedTuple):  # The URL that the link points at
                    base:     Optional[URLReference]          # Probably the same URL as pageurl below, but possibly different if <base href> (in which case result.linkurl.base.base is the original pageurl)
                    ref:      str                             # The original form of the URL reference (e.g. 'href') from the page being checked
                    resolved: str                             # 'ref', but resolved to be an absolute URL; both by combining it with 'base', and by following any redirects
                pageurl: NamedTuple:                      # The URL of the page that this link was found on
                    ref:      str                             # The original request URL
                    resolved: str                             # 'ref', but after following any redirects
                html:    bs4.element.Tag                  # The HTML tag that contained the link

        The 'broken' argument is a string identifying why the link is
        considered broken, or is None if the link is not broken.

        """
        pass

    def handle_page_error(self, url: str, err: str) -> None:
        """handle_page_error is a hook; called whenever we encounter an error
        proccessing a page that we've been told to check for broken
        links on.  This could be because we failed to fetch the page,
        or it could be because of an HTML-parsing error.

        """
        pass

    def handle_backoff(self, url: str, secs: int) -> None:
        """handle_backoff is a hook; called whenever we encounter an HTTP 429
        response telling us to backoff for a number of seconds.

        """
