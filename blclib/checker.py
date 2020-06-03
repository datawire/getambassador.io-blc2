from http.client import HTTPMessage
from queue import Queue
from typing import Dict, Set, Union, Optional #, Iterable, NamedTuple
from urllib.parse import urldefrag

# import bs4.element
import requests
from bs4 import BeautifulSoup

# from .data_uri import DataAdapter
from .httpcache import HTTPClient
from .models import Link, URLReference

def get_content_type(resp: requests.Response) -> str:
    msg = HTTPMessage()
    msg['content-type'] = resp.headers.get('content-type', None)
    return msg.get_content_type()


class BaseChecker:

    _client = HTTPClient()
    _bodycache: Dict[str, Union[BeautifulSoup, str]] = dict()
    _queue: 'Queue[Union[Link,URLReference]]' = Queue()
    _done_pages: Set[str] = set()

    def __init__(self):
        self._client.mount('data:', DataAdapter())

    def enqueue(self, task: Union[Link,URLReference]) -> None:
        """enqueue a task fro the checker to do.
        If the task is a...

          - URLReference: Check the page pointed to by this URL for
            broken links; call handle_page_starting() and possibly
            handle_page_error(); enqueue all links found on the page.

          - Link: Check if the link is broken; then call
            handle_link_result().

        """
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
        resp: Union[requests.Response, str] = "HTTP_unknown"
        try:
            resp = self._client.get(url)
            if resp.status_code != 200:
                resp = f"HTTP_{resp.status_code}"
        except BaseException as err:
            resp = f"{err}"
        return resp

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
                        soup = BeautifulSoup(resp.text, 'html.parser')
                    except BaseException as err:
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
        resp = self._client.get(link.linkurl.resolved)
        if isinstance(resp, str):
            return resp
        link = link._replace(
            linkurl=link.linkurl._replace(
                resolved=resp.url))

        # Check the fragment
        fragment = urldefrag(link.linkurl.resolved).fragment
        if fragment:
            soup = self._get_soup(link.linkurl.resolved)
            if isinstance(soup, str):
                return f"fragment: {soup}"
            if not soup.find(id=fragment):
                return f"fragment: no element with that id"

        return None

    def _process_html(
        self,
        page_url: URLReference,
        page_soup: BeautifulSoup,
    ) -> None:
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
                    self.enqueue(Link(
                        linkurl=link_url,
                        pageurl=page_url,
                        html=element
                    ))

    def _check_page(self, page_url: URLReference) -> None:
        # Log that we're starting
        if urldefrag(page_url.resolved) in self._done_pages:
            return
        self.handle_page_starting(page_url.resolved)

        # Resolve any redirects
        page_resp = self._get_resp(page_url.resolved)
        if isinstance(page_resp, str):
            self.handle_page_error(page_url.resolved, page_resp)
            self._done_pages.add(page_url.resolved)
            return
        page_url = page_url._replace(resolved=page_resp.url)
        if urldefrag(page_url.resolved).url in self._done_pages:
            return

        # Parse the page
        page_soup = self._get_soup(page_url.resolved)
        if isinstance(page_soup, str):
            self.handle_page_error(page_url.resolved, page_soup)
            self._done_pages.add(page_url.resolved)
            return
        
        # Inspect the page for bad links
        self._process_html(page_url, page_soup)

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
