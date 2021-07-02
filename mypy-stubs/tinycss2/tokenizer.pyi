import typing

from . import ast
from .ast import AtKeywordToken as AtKeywordToken
from .ast import Comment as Comment
from .ast import CurlyBracketsBlock as CurlyBracketsBlock
from .ast import DimensionToken as DimensionToken
from .ast import FunctionBlock as FunctionBlock
from .ast import HashToken as HashToken
from .ast import IdentToken as IdentToken
from .ast import LiteralToken as LiteralToken
from .ast import NumberToken as NumberToken
from .ast import ParenthesesBlock as ParenthesesBlock
from .ast import ParseError as ParseError
from .ast import PercentageToken as PercentageToken
from .ast import SquareBracketsBlock as SquareBracketsBlock
from .ast import StringToken as StringToken
from .ast import UnicodeRangeToken as UnicodeRangeToken
from .ast import URLToken as URLToken
from .ast import WhitespaceToken as WhitespaceToken
from .serializer import serialize_string_value as serialize_string_value
from .serializer import serialize_url as serialize_url

def parse_component_value_list(
    css: str, skip_comments: bool = ...
) -> typing.List[ast._ComponentValue]: ...
