#!/usr/bin/env python3

import sys
from copy import deepcopy
from http.client import HTTPMessage
from typing import Dict, Iterable, Optional
from urllib.parse import urldefrag

import requests
from bs4 import BeautifulSoup  # type: ignore


class Client(requests.Session):

    _cache: Dict[str, requests.Response] = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_adapter(self, url):
        client = self
        inner = super().get_adapter(url)

        class AdapterWrapper:
            def send(self, req, **kwargs):
                cachekey = client._cache_key(req)
                if cachekey and cachekey in client._cache:
                    resp = deepcopy(client._cache[cachekey])
                    resp.url = req.url
                    resp.request = req
                else:
                    resp = inner.send(req, **kwargs)
                    if cachekey:
                        client._cache[cachekey] = resp

                return resp

        return AdapterWrapper()

    def _cache_key(self, req: requests.Request) -> Optional[str]:
        if req.method != "GET":
            return None
        return f"{req.method} {urldefrag(req.url).url}"


def get_content_type(resp: requests.Response) -> str:
    msg = HTTPMessage()
    msg['content-type'] = resp.headers.get('content-type', None)
    return msg.get_content_type()


class Checker:

    _client = Client()
    _bodycache: Dict[str, Optional[BeautifulSoup]] = dict()

    def enqueue(self, url: str) -> None:
        pass

    def run(self) -> None:
        pass

    def get_links(self, soup: BeautifulSoup) -> List:
        pass

    def get_resp(self, url) -> Optional[requests.Response]:
        resp: Optional[requests.Response] = None
        try:
            resp = self._client.get(url)
            if resp.status_code != 200:
                resp = None
        except:
            resp = None
        return resp

    def get_soup(self, url) -> Optional[BeautifulSoup]:
        baseurl = urldefrag(url).url
        if baseurl not in self._bodycache:
            soup: Optional[BeautifulSoup] = None

            resp = self.get_resp(url)
            if resp:
                content_type = get_content_type(resp)
                if content_type == 'text/html':
                    try:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                    except:
                        soup = None

            self._bodycache[baseurl] = soup
        return self._bodycache[baseurl]

    def target_exists(self, url) -> bool:
        resp = self.get_resp(url)
        if not resp:
            return False

        baseurl, fragment = urldefrag(url)
        if fragment:
            soup = self.get_soup(url)
            if not soup:
                return False
            if not soup.find(id=fragment):
                return False

        return True


def main(urls: Iterable[str]) -> None:
    checker = Checker()
    for url in urls:
        checker.enqueue(url)
    checker.run()


if __name__ == "__main__":
    main(sys.argv[1:])
