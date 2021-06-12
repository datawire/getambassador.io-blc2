from copy import deepcopy
from time import sleep
from typing import Callable, Container, Dict, Mapping, Optional, Text, Tuple, Union
from urllib.parse import urldefrag

import requests
import requests.models


class HTTPClient(requests.Session):

    _cache: Dict[str, requests.Response] = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_adapter(self, url):
        client = self
        inner = super().get_adapter(url)

        class AdapterWrapper:
            def send(
                self,
                req: requests.models.PreparedRequest,
                stream: bool = False,
                timeout: Union[None, float, Tuple[float, float], Tuple[float, None]] = None,
                verify: Union[bool, str] = True,
                cert: Union[None, Union[bytes, Text], Container[Union[bytes, Text]]] = None,
                proxies: Optional[Mapping[str, str]] = None,
            ) -> requests.models.Response:
                cachekey = client._cache_key(req)
                if cachekey and cachekey in client._cache:
                    resp = deepcopy(client._cache[cachekey])
                    resp.url = req.url
                    resp.request = req
                else:
                    client.hook_before_send(
                        req,
                        stream=stream,
                        timeout=timeout,
                        verify=verify,
                        cert=cert,
                        proxies=proxies,
                    )
                    resp = inner.send(
                        req,
                        stream=stream,
                        timeout=timeout,
                        verify=verify,
                        cert=cert,
                        proxies=proxies,
                    )
                    if (
                        resp.status_code == 429
                        and resp.headers.get('retry-after', 'x').isnumeric()
                    ):
                        secs = int(resp.headers.get('retry-after'))
                        client.hook_before_sleep(
                            secs,
                            req,
                            stream=stream,
                            timeout=timeout,
                            verify=verify,
                            cert=cert,
                            proxies=proxies,
                        )
                        sleep(secs)
                        return self.send(
                            req,
                            stream=stream,
                            timeout=timeout,
                            verify=verify,
                            cert=cert,
                            proxies=proxies,
                        )
                    if cachekey:
                        client._cache[cachekey] = resp

                return resp

        return AdapterWrapper()

    def _cache_key(self, req: requests.Request) -> Optional[str]:
        if req.method != "GET":
            return None
        return f"{req.method} {urldefrag(req.url).url}"

    def hook_before_send(
        self,
        request: requests.models.PreparedRequest,
        stream: bool = False,
        timeout: Union[None, float, Tuple[float, float], Tuple[float, None]] = None,
        verify: Union[bool, str] = True,
        cert: Union[None, Union[bytes, Text], Container[Union[bytes, Text]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Override this to provide a callback that is called before making a
        (non-cached) request.

        """
        pass

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
        """Override this to provide a callback that is called before sleeping
        to back-off from an overloaded server.

        """
        pass
