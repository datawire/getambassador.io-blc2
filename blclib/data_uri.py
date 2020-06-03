import io
from urllib.parse import unquote_to_bytes

from requests.adapters import BaseAdapter, HTTPAdapter
from requests.exceptions import InvalidURL
from requests.models import Response
from requests.utils import get_encoding_from_headers
from urllib3.response import HTTPResponse


class DataAdapter(BaseAdapter):
    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None,
    ):
        try:
            # This is very similar to the parser in
            # urllib.request.DataHandler in the standard library.
            scheme, data = request.url.split(':', 1)
            mediatype, data = data.split(',', 1)

            data = unquote_to_bytes(data)
            if mediatype.endswith(';base64'):
                data = base64.decodebytes(data)
                mediatype = mediatype[: -len(';base64')]

            if not mediatype:
                mediatype = "text/plain;charset=US-ASCII"
        except BaseException as err:
            raise InvalidURL(err, request=request)

        # Now pack that info in to a urllib3.response.HTTPResponse.
        u3resp = HTTPResponse(
            status=200,
            reason='OK',
            headers={'Content-Type': mediatype, 'Content-Length': len(data),},
            body=data,
        )

        # Now pack that info in to a requests.models.Response.
        return HTTPAdapter.build_response(self, request, u3resp)
