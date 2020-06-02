from typing import Any, Optional

from .element import Tag


class GuessedAtParserWarning(UserWarning):
    ...


class MarkupResemblesLocatorWarning(UserWarning):
    ...


class BeautifulSoup(Tag):
    ROOT_TAG_NAME: str = ...
    DEFAULT_BUILDER_FEATURES: Any = ...
    ASCII_SPACES: str = ...
    NO_PARSER_SPECIFIED_WARNING: str = ...
    element_classes: Any = ...
    builder: Any = ...
    is_xml: Any = ...
    known_xml: Any = ...
    parse_only: Any = ...
    markup: Any = ...

    def __init__(self,
                 markup: str = ...,
                 features: Optional[Any] = ...,
                 builder: Optional[Any] = ...,
                 parse_only: Optional[Any] = ...,
                 from_encoding: Optional[Any] = ...,
                 exclude_encodings: Optional[Any] = ...,
                 element_classes: Optional[Any] = ...,
                 **kwargs: Any):
        ...

    def __copy__(self):
        ...

    current_data: Any = ...
    currentTag: Any = ...
    tagStack: Any = ...
    preserve_whitespace_tag_stack: Any = ...
    string_container_stack: Any = ...

    def reset(self) -> None:
        ...

    def new_tag(self,
                name: Any,
                namespace: Optional[Any] = ...,
                nsprefix: Optional[Any] = ...,
                attrs: Any = ...,
                sourceline: Optional[Any] = ...,
                sourcepos: Optional[Any] = ...,
                **kwattrs: Any):
        ...

    def string_container(self, base_class: Optional[Any] = ...):
        ...

    def new_string(self, s: Any, subclass: Optional[Any] = ...):
        ...

    def insert_before(self, *args: Any) -> None:
        ...

    def insert_after(self, *args: Any) -> None:
        ...

    def popTag(self):
        ...

    def pushTag(self, tag: Any) -> None:
        ...

    def endData(self, containerClass: Optional[Any] = ...) -> None:
        ...

    def object_was_parsed(self,
                          o: Any,
                          parent: Optional[Any] = ...,
                          most_recent_element: Optional[Any] = ...) -> None:
        ...

    def handle_starttag(self,
                        name: Any,
                        namespace: Any,
                        nsprefix: Any,
                        attrs: Any,
                        sourceline: Optional[Any] = ...,
                        sourcepos: Optional[Any] = ...):
        ...

    def handle_endtag(self, name: Any, nsprefix: Optional[Any] = ...) -> None:
        ...

    def handle_data(self, data: Any) -> None:
        ...

    def decode(
        self,
        pretty_print: bool = ...,
        indent_level: Optional[Any] = ...,
        eventual_encoding: Any = ...,
        formatter: str = ...,
    ):
        ...


class BeautifulStoneSoup(BeautifulSoup):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...


class StopParsing(Exception):
    ...


class FeatureNotFound(ValueError):
    ...
