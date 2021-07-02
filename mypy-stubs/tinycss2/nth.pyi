import re
import typing

from . import ast

def parse_nth(
    input: typing.Union[str, typing.Iterable[ast._ComponentValue]]
) -> typing.Tuple[int, int]: ...

N_DASH_DIGITS_RE: re.Pattern[str]
