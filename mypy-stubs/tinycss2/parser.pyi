import typing

from . import ast
from .ast import AtRule as AtRule
from .ast import Declaration as Declaration
from .ast import ParseError as ParseError
from .ast import QualifiedRule as QualifiedRule
from .tokenizer import parse_component_value_list as parse_component_value_list

_Input = typing.Union[str, typing.Iterable[ast._ComponentValue]]

def parse_one_component_value(
    input: _Input, skip_comments: bool = ...
) -> typing.Union[ast._ComponentValue, ast.ParseError]: ...
def parse_one_declaration(
    input: _Input, skip_comments: bool = ...
) -> typing.Union[ast.Declaration, ast.ParseError]: ...
def parse_declaration_list(
    input: _Input, skip_comments: bool = ..., skip_whitespace: bool = ...
) -> typing.Union[
    ast.Declaration,
    ast.AtRule,
    ast.Comment,
    ast.WhitespaceToken,
    ast.ParseError,
]: ...
def parse_one_rule(input: _Input, skip_comments: bool = ...) -> typing.Union[
    ast.QualifiedRule,
    ast.AtRule,
    ast.ParseError,
]: ...
def parse_rule_list(
    input: _Input, skip_comments: bool = ..., skip_whitespace: bool = ...
) -> typing.Iterator[ast._TopLevel]: ...
def parse_stylesheet(
    input: _Input, skip_comments: bool = ..., skip_whitespace: bool = ...
) -> typing.Iterator[ast._TopLevel]: ...
