import os
import re
import time
from http.client import HTTPMessage
from typing import Container, Dict, List, Mapping, Optional, Set, Text, Tuple, Union
from urllib.parse import urldefrag, urlparse

import bs4.element
import requests
import tinycss2
from bs4 import BeautifulSoup
from requests.utils import parse_header_links

from .data_uri import DataAdapter
from .httpcache import HTTPClient as BaseHTTPClient
from .httpcache import RetryAfterException
from .models import Link, URLReference

USER_AGENT = os.getenv('USER_AGENT', 'github.com/datawire/getambassador.io-blc2')


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


def task_netloc(task: Union[Link, URLReference]) -> str:
    if isinstance(task, Link):
        return urlparse(task.linkurl.resolved).netloc
    elif isinstance(task, URLReference):
        return urlparse(task.resolved).netloc
    else:
        assert False


# types-beautifulsoup4 4.10 says that bs4.element.Tag.get returns `str | list[str] | None`,
# which I'm pretty sure is wrong, I don't think it's actually possible for it to return a
# list[str].  So, uh, have this little assertion validate that belief.
def get_tag_attr(tag: bs4.element.Tag, attrname: str) -> Optional[str]:
    ret = tag.get(attrname)
    assert (ret is None) or isinstance(ret, str)
    return ret


class BaseChecker:

    _client: HTTPClient
    _bodycache: Dict[str, Union[BeautifulSoup, str]] = dict()
    _queue: List[Union[Link, URLReference]] = []
    _queued_pages: Set[str] = set()
    _done_pages: Set[str] = set()
    _user_agent_for_link: Dict[str, str] = dict()

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
        self._queue.append(task)

    def run(self) -> None:
        """Run the checker; keep running tasks until the queue (see
        `enqueue()`) is empty.

        """
        not_before: Dict[str, float] = {}
        while self._queue:
            task = self._queue[0]
            self._queue = self._queue[1:]
            now = time.time()
            if not_before.get(task_netloc(task), 0) < now:
                try:
                    if isinstance(task, Link):
                        self._check_link(task)
                    elif isinstance(task, URLReference):
                        self._check_page(task)
                    else:
                        assert False
                except RetryAfterException as err:
                    self.handle_429(err)
                    not_before[urlparse(err.url).netloc] = time.time() + err.retry_after
                    self.enqueue(task)
            else:
                times = [not_before.get(task_netloc(ot), 0) for ot in self._queue]
                if any(ts < now for ts in times):
                    # There's other stuff to do in the mean-time, just queue it again after
                    # that stuff.
                    self.enqueue(task)
                else:
                    # There's nothing to do but sleep
                    secs = min(times) - now
                    self.handle_sleep(secs)
                    time.sleep(secs)
                    self.enqueue(task)

    def _get_user_agent(self, url: str) -> str:
        return self._user_agent_for_link.get(url, USER_AGENT)

    def _get_resp(self, url: str) -> Union[requests.Response, str]:
        try:
            resp: requests.Response = self._client.get(
                url,
                headers={
                    'User-Agent': self._get_user_agent(url),
                },
                timeout=10,
            )
            if resp.status_code != 200:
                reterr = f"HTTP_{resp.status_code}"
                if resp.status_code == 429 or int(resp.status_code / 100) == 5:
                    # Report it as an error (instead of just as a broken link)
                    self.handle_page_error(url, reterr)
                return reterr
            return resp
        except RetryAfterException as err:
            raise err
        except requests.exceptions.Timeout as err:
            reterr = f"HTTP_TIMEOUT"
            self.handle_page_error(url, reterr)
            return reterr
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
                if content_type == 'text/html' or content_type == 'image/svg+xml':
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
                return f"fragment: no element with that id/name={repr(fragment)}"

        return None

    @staticmethod
    def _parse_srcset_value(attrvalue: str) -> List:
        return [desc.split()[0] for desc in attrvalue.split(',')]

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
            href = get_tag_attr(base_tags[0], 'href')
            assert isinstance(href, str)
            base_url = base_url.parse(href)

        for tagname, attrs in selectors.items():
            for attrname in attrs:
                for element in page_soup.select(f"{tagname}[{attrname}]"):
                    attrvalue = get_tag_attr(element, attrname)
                    assert isinstance(attrvalue, str)
                    url_strs: List[str] = []

                    if attrname == 'content':
                        if (get_tag_attr(element, 'http-equiv') or '').lower() == 'refresh':
                            # https://html.spec.whatwg.org/multipage/semantics.html#attr-meta-http-equiv-refresh
                            url = url_from_meta_http_equiv_refresh(attrvalue)
                            if url:
                                url_strs = [url]
                    elif attrname == 'ping':
                        # https://html.spec.whatwg.org/multipage/links.html#ping
                        url_strs = [x for x in attrvalue.split()]
                    elif attrname == 'srcset':
                        # https://html.spec.whatwg.org/multipage/images.html#srcset-attributes
                        url_strs = self._parse_srcset_value(attrvalue)
                    else:
                        url_strs = [attrvalue]

                    for url_str in url_strs:
                        link_url = base_url.parse(url_str)
                        self.handle_link(
                            Link(linkurl=link_url, pageurl=page_url, html=element)
                        )
        for element in page_soup.select('style'):
            assert element.string
            self._process_css(
                page_url=page_url, base_url=base_url, css_str=element.string, tag=element
            )
        self.handle_html_extra(page_url=page_url, page_soup=page_soup)

    def _process_css(
        self,
        page_url: URLReference,
        base_url: URLReference,
        css_str: str,
        tag: Optional[bs4.element.Tag] = None,
    ) -> None:
        rules = tinycss2.parse_stylesheet(css_str)
        errors = [rule for rule in rules if isinstance(rule, tinycss2.ast.ParseError)]
        if errors:
            self.handle_page_error(page_url.resolved, f"{errors[0]}")
        for rule in rules:
            if isinstance(rule, tinycss2.ast.QualifiedRule) or isinstance(
                rule, tinycss2.ast.AtRule
            ):
                if rule.content:
                    for component in rule.content:
                        if isinstance(component, tinycss2.ast.URLToken):
                            link_url = base_url.parse(component.value)
                            self.handle_link(
                                Link(linkurl=link_url, pageurl=page_url, html=tag)
                            )

    def _check_page(self, page_url: URLReference) -> None:
        # Handle redirects
        page_resp = self._get_resp(page_url.resolved)
        if isinstance(page_resp, str):
            page_clean_url = urldefrag(page_url.resolved).url
            self._done_pages.add(page_clean_url)
            self.handle_page_starting(page_clean_url)
            if page_resp == "HTTP_TIMEOUT":
                self.handle_timeout(page_clean_url, page_resp)
            else:
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

        # Inspect the headers for bad links ##############################################

        for link in parse_header_links(page_resp.headers.get('link', '')):
            link_url = page_url.parse(link['url'])
            self.handle_link(Link(linkurl=link_url, pageurl=page_url, html=None))

        if sourcemap_url := page_resp.headers.get('sourcemap', ''):
            link_url = page_url.parse(sourcemap_url)
            self.handle_link(Link(linkurl=link_url, pageurl=page_url, html=None))

        # Inspect the page for bad links #################################################

        content_type = get_content_type(page_resp)
        if content_type == 'application/javascript':
            if m := re.search(
                r'^/\*! For license information please see (\S+) \*/', page_resp.text
            ):
                link_url = page_url.parse(m[1])
                self.handle_link(Link(linkurl=link_url, pageurl=page_url, html=None))
            if m := re.search(r'//[#@] sourceMappingURL=(\S+)\n?$', page_resp.text):
                # sourcemap v3 https://docs.google.com/document/d/1U1RGAehQwRypUTovF1KRlpiOFze0b-_2gc6fAH0KY0k/edit#
                link_url = page_url.parse(m[1])
                self.handle_link(Link(linkurl=link_url, pageurl=page_url, html=None))
            # TODO: check for ES6 imports
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
        elif content_type == 'image/vnd.microsoft.icon':
            pass  # nothing to do
        elif content_type == 'application/vnd.ms-fontobject':
            pass  # nothing to do
        elif content_type == 'font/ttf':
            pass  # nothing to do
        elif content_type == 'font/woff':
            pass  # nothing to do
        elif content_type == 'font/woff2':
            pass  # nothing to do
        elif content_type == 'text/css':
            self._process_css(page_url=page_url, base_url=page_url, css_str=page_resp.text)
        elif content_type == 'text/html':
            page_soup = self._get_soup(page_clean_url)
            if isinstance(page_soup, str):
                self.handle_page_error(page_clean_url, page_soup)
                return
            self._process_html(page_url, page_soup)
        elif content_type == 'text/plain':
            pass  # nothing to do
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

    def handle_html_extra(self, page_url: URLReference, page_soup: BeautifulSoup) -> None:
        """handle_html_extra is a hook; called for each page we process.  This
        allows an application to do extra validation of the HTML beyond what is
        built in to blclib.

        """
        pass

    def handle_link(self, link: Link) -> None:
        """handle_link is a hook; called whenever a link is found in a page.
        Unlike most of the hooks, the default behavior is non-empty;
        the default behavior os to call Checker.enqueue(link) to queue
        the link to be checked.  You can override this to filter
        certain links out.

        """

        self.enqueue(link)

    def handle_link_result(self, link: Link, broken: Optional[str]) -> None:
        """handle_link_result is a hook; called for each link found in a page.

        Using a Python-ish pseudo-code notation to express the
        structure and semantics of the 'link' argument:

          class Link:

            linkurl: class URLReference:        # '.linkurl' is the URL that the link points at.
              base:     Optional[URLReference]  # '.linkurl.base' is probably the same URL as '.pageurl' below, but possibly different if <base href> is set (in which case '.linkurl.base.base' is the original '.pageurl').
              ref:      str                     # '.linkurl.ref' is the original form of the URL reference (e.g. the thing in 'href') from the page being checked.
              resolved: str                     # '.linkurl.resolved' is '.linkurl.ref', but resolved to be an absolute URL; both by combining it with '.linkurl.base', and by following any redirects.
            pageurl: class URLReference:        # '.pageurl' is the URL of the page that this link was found on.
              base:     Optional[URLReference]  # '.pageurl.base' is always 'None'.
              ref:      str                     # '.pageurl.ref' is the original request URL.
              resolved: str                     # '.pageurl.resolved' is '.pageurl.ref', but after following any redirects.
            html:    Optional[bs4.element.Tag]  # '.html' is the HTML tag that contained the link.  May be None if linked to from other resources, like an external stylsheet.

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

    def handle_timeout(self, url: str, err: str) -> None:
        """handle_timeout is a hook; called whenever we encounter an http timeout error.
        This could be because the user agent or the ip address is not allowed
        by the remote site
        """
        pass

    def handle_429(self, err: RetryAfterException) -> None:
        """handle_429 is a hook; called whenever we encounter an HTTP 429
        response telling us to backoff for a number of seconds.

        """
        pass

    def handle_sleep(self, secs: float) -> None:
        """handle_sleep is a hook; called before sleeping whenever we have nothing else to do but
        wait {secs} seconds until our 429s have expired.

        """
        pass
