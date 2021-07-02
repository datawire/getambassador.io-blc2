import typing

from .serializer import serialize_identifier as serialize_identifier
from .serializer import serialize_name as serialize_name

class Node:
    type: str
    source_line: int
    source_column: int
    def __init__(self, source_line: int, source_column: int) -> None: ...
    def serialize(self) -> str: ...

class ParseError(Node):
    kind: str
    message: str
    def __init__(self, line: int, column: int, kind: str, message: str) -> None: ...

class Comment(Node):
    value: str
    def __init__(self, line: int, column: int, value: str) -> None: ...

class WhitespaceToken(Node):
    value: str
    def __init__(self, line: int, column: int, value: int) -> None: ...

class LiteralToken(Node):
    value: str
    def __init__(self, line: int, column: int, value: str) -> None: ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __ne__(self, other: typing.Any) -> bool: ...

class IdentToken(Node):
    value: str
    lower_value: str
    def __init__(self, line: int, column: int, value: str) -> None: ...

class AtKeywordToken(Node):
    value: str
    lower_value: str
    def __init__(self, line: int, column: int, value: str) -> None: ...

class HashToken(Node):
    value: str
    is_identifier: bool
    def __init__(self, line: int, column: int, value: str, is_identifier: bool) -> None: ...

class StringToken(Node):
    value: str
    representation: str
    def __init__(self, line: int, column: int, value: str, representation: str) -> None: ...

class URLToken(Node):
    value: str
    representation: str
    def __init__(self, line: int, column: int, value: str, representation: str) -> None: ...

class UnicodeRangeToken(Node):
    start: int
    end: int
    def __init__(self, line: int, column: int, start: int, end: int) -> None: ...

class NumberToken(Node):
    value: float
    int_value: typing.Optional[int]
    is_integer: bool
    representation: str
    def __init__(
        self,
        line: int,
        column: int,
        value: float,
        int_value: typing.Optional[int],
        representation: str,
    ) -> None: ...

class PercentageToken(Node):
    value: float
    int_value: typing.Optional[int]
    is_integer: bool
    representation: str
    def __init__(
        self,
        line: int,
        column: int,
        value: float,
        int_value: typing.Optional[int],
        representation: str,
    ) -> None: ...

class DimensionToken(Node):
    value: float
    int_value: typing.Optional[int]
    is_integer: bool
    representation: str
    unit: str
    lower_unit: str
    def __init__(
        self,
        line: int,
        column: int,
        value: float,
        int_value: typing.Optional[int],
        representation: str,
        unit: str,
    ) -> None: ...

class ParenthesesBlock(Node):
    content: typing.List['_ComponentValue']
    def __init__(
        self, line: int, column: int, content: typing.List['_ComponentValue']
    ) -> None: ...

class SquareBracketsBlock(Node):
    content: typing.List['_ComponentValue']
    def __init__(
        self, line: int, column: int, content: typing.List['_ComponentValue']
    ) -> None: ...

class CurlyBracketsBlock(Node):
    content: typing.List['_ComponentValue']
    def __init__(
        self, line: int, column: int, content: typing.List['_ComponentValue']
    ) -> None: ...

class FunctionBlock(Node):
    name: str
    lower_name: str
    arguments: typing.List['_ComponentValue']
    def __init__(
        self, line: int, column: int, name: str, arguments: typing.List['_ComponentValue']
    ) -> None: ...

class Declaration(Node):
    name: str
    lower_name: str
    value: typing.List['_ComponentValue']
    important: bool
    def __init__(
        self,
        line: int,
        column: int,
        name: str,
        lower_name: str,
        value: typing.List['_ComponentValue'],
        important: bool,
    ) -> None: ...

class QualifiedRule(Node):
    prelude: typing.List['_ComponentValue']
    content: typing.List['_ComponentValue']
    def __init__(
        self,
        line: int,
        column: int,
        prelude: typing.List['_ComponentValue'],
        content: typing.List['_ComponentValue'],
    ) -> None: ...

class AtRule(Node):
    at_keyword: str
    lower_at_keyword: str
    prelude: typing.List['_ComponentValue']
    content: typing.Optional[typing.List['_ComponentValue']]
    def __init__(
        self,
        line: int,
        column: int,
        at_keyword: str,
        lower_at_keyword: str,
        prelude: typing.List['_ComponentValue'],
        content: typing.Optional[typing.List['_ComponentValue']],
    ) -> None: ...

_TopLevel = typing.Union[
    QualifiedRule,
    AtRule,
    Comment,
    WhitespaceToken,
    ParseError,
]

_ComponentValue = typing.Union[
    ParseError,
    WhitespaceToken,
    LiteralToken,
    IdentToken,
    AtKeywordToken,
    HashToken,
    StringToken,
    URLToken,
    NumberToken,
    PercentageToken,
    DimensionToken,
    UnicodeRangeToken,
    ParenthesesBlock,
    SquareBracketsBlock,
    CurlyBracketsBlock,
    FunctionBlock,
    Comment,
]
