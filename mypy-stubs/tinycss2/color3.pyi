import typing

from . import ast
from .parser import parse_one_component_value as parse_one_component_value

class RGBA(typing.NamedTuple):
    red: float
    green: float
    blue: float
    alpha: float

def parse_color(
    input: typing.Union[str, ast._ComponentValue]
) -> typing.Union[None, str, RGBA]: ...
