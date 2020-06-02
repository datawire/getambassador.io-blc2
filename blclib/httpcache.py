from copy import deepcopy
from typing import Dict, Optional
from urllib.parse import urldefrag

import requests


class HTTPClient(requests.Session):

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
