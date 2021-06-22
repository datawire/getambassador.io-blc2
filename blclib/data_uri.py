import base64
import io
from typing import Container, Mapping, Optional, Text, Tuple, Union, cast
from urllib.parse import unquote_to_bytes

import requests.models
from requests.adapters import BaseAdapter, HTTPAdapter
from requests.exceptions import InvalidURL
from urllib3.response import HTTPResponse


class DataAdapter(BaseAdapter):
    def send(
        self,
        request: requests.models.PreparedRequest,
        stream: bool = False,
        timeout: Union[None, float, Tuple[float, float], Tuple[float, None]] = None,
        verify: Union[bool, str] = True,
        cert: Union[None, Union[bytes, Text], Container[Union[bytes, Text]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> requests.models.Response:
        try:
            # This is very similar to the parser in
            # urllib.request.DataHandler in the standard library.
            assert request.url
            scheme, data_str = request.url.split(':', 1)
            mediatype, data_str = data_str.split(',', 1)

            data_bytes = unquote_to_bytes(data_str)
            if mediatype.endswith(';base64'):
                data_bytes = base64.decodebytes(data_bytes)
                mediatype = mediatype[: -len(';base64')]

            if not mediatype:
                mediatype = "text/plain;charset=US-ASCII"
        except BaseException as err:
            raise InvalidURL(err, request=request)

        # Now pack that info in to a urllib3.response.HTTPResponse.
        u3resp = HTTPResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': mediatype,
                'Content-Length': str(len(data_bytes)),
            },
            body=io.BytesIO(data_bytes),
        )

        # Now pack that info in to a requests.models.Response.
        return HTTPAdapter.build_response(cast(HTTPAdapter, self), request, u3resp)

    def close(self) -> None:
        pass
