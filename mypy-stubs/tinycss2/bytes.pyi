import typing

import webencodings

from . import ast
from .parser import parse_stylesheet as parse_stylesheet

def decode_stylesheet_bytes(
    css_bytes: str,
    protocol_encoding: typing.Optional[str] = ...,
    environment_encoding: typing.Optional[webencodings.Encoding] = ...,
) -> typing.Tuple[str, webencodings.Encoding]: ...
def parse_stylesheet_bytes(
    css_bytes: str,
    protocol_encoding: typing.Optional[str] = ...,
    environment_encoding: typing.Optional[webencodings.Encoding] = ...,
    skip_comments: bool = ...,
    skip_whitespace: bool = ...,
) -> typing.Tuple[typing.List[ast._TopLevel], webencodings.Encoding]: ...
