from typing import Any, Optional, Union

DEFAULT_OUTPUT_ENCODING: str
PY3K: Any
nonwhitespace_re: Any
whitespace_re: Any
PYTHON_SPECIFIC_ENCODINGS: Any

class NamespacedAttribute(str):
    def __new__(
        cls,
        prefix: Any,
        name: Optional[Any] = ...,
        namespace: Optional[Any] = ...,
    ): ...

class AttributeValueWithCharsetSubstitution(str): ...

class PageElement:
    parent: Any = ...
    previous_element: Any = ...
    next_element: Any = ...
    next_sibling: Any = ...
    previous_sibling: Any = ...
    def setup(
        self,
        parent: Optional[Any] = ...,
        previous_element: Optional[Any] = ...,
        next_element: Optional[Any] = ...,
        previous_sibling: Optional[Any] = ...,
        next_sibling: Optional[Any] = ...,
    ) -> None: ...
    def format_string(self, s: Any, formatter: Any): ...
    def formatter_for_name(self, formatter: Any): ...
    nextSibling: Any = ...
    previousSibling: Any = ...
    def replace_with(self, replace_with: Any): ...
    replaceWith: Any = ...
    def unwrap(self): ...
    replace_with_children: Any = ...
    replaceWithChildren: Any = ...
    def wrap(self, wrap_inside: Any): ...
    def extract(self, _self_index: Optional[Any] = ...): ...
    def insert(self, position: Any, new_child: Any) -> None: ...
    def append(self, tag: Any) -> None: ...
    def extend(self, tags: Any) -> None: ...
    def insert_before(self, *args: Any) -> None: ...
    def insert_after(self, *args: Any) -> None: ...
    def find_next(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findNext: Any = ...
    def find_all_next(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findAllNext: Any = ...
    def find_next_sibling(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findNextSibling: Any = ...
    def find_next_siblings(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findNextSiblings: Any = ...
    fetchNextSiblings: Any = ...
    def find_previous(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findPrevious: Any = ...
    def find_all_previous(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findAllPrevious: Any = ...
    fetchPrevious: Any = ...
    def find_previous_sibling(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findPreviousSibling: Any = ...
    def find_previous_siblings(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findPreviousSiblings: Any = ...
    fetchPreviousSiblings: Any = ...
    def find_parent(self, name: Optional[Any] = ..., attrs: Any = ..., **kwargs: Any): ...
    findParent: Any = ...
    def find_parents(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findParents: Any = ...
    fetchParents: Any = ...
    @property
    def next(self): ...
    @property
    def previous(self): ...
    @property
    def next_elements(self) -> None: ...
    @property
    def next_siblings(self) -> None: ...
    @property
    def previous_elements(self) -> None: ...
    @property
    def previous_siblings(self) -> None: ...
    @property
    def parents(self) -> None: ...
    @property
    def decomposed(self): ...
    def nextGenerator(self): ...
    def nextSiblingGenerator(self): ...
    def previousGenerator(self): ...
    def previousSiblingGenerator(self): ...
    def parentGenerator(self): ...

class NavigableString(str, PageElement):
    PREFIX: str = ...
    SUFFIX: str = ...
    known_xml: Any = ...
    def __new__(cls, value: Any): ...
    def __copy__(self): ...
    def __getnewargs__(self): ...
    def __getattr__(self, attr: Any): ...
    def output_ready(self, formatter: str = ...): ...
    @property
    def name(self) -> None: ...
    @name.setter
    def name(self, name: Any) -> None: ...

class PreformattedString(NavigableString):
    PREFIX: str = ...
    SUFFIX: str = ...
    def output_ready(self, formatter: Optional[Any] = ...): ...

class CData(PreformattedString):
    PREFIX: str = ...
    SUFFIX: str = ...

class ProcessingInstruction(PreformattedString):
    PREFIX: str = ...
    SUFFIX: str = ...

class XMLProcessingInstruction(ProcessingInstruction):
    PREFIX: str = ...
    SUFFIX: str = ...

class Comment(PreformattedString):
    PREFIX: str = ...
    SUFFIX: str = ...

class Declaration(PreformattedString):
    PREFIX: str = ...
    SUFFIX: str = ...

class Doctype(PreformattedString):
    @classmethod
    def for_name_and_ids(cls, name: Any, pub_id: Any, system_id: Any): ...
    PREFIX: str = ...
    SUFFIX: str = ...

class Stylesheet(NavigableString): ...
class Script(NavigableString): ...
class TemplateString(NavigableString): ...

class Tag(PageElement):
    parser_class: Any = ...
    name: Any = ...
    namespace: Any = ...
    prefix: Any = ...
    sourceline: Any = ...
    sourcepos: Any = ...
    known_xml: Any = ...
    attrs: Any = ...
    contents: Any = ...
    hidden: Union[bool, int] = ...
    can_be_empty_element: Any = ...
    cdata_list_attributes: Any = ...
    preserve_whitespace_tags: Any = ...
    def __init__(
        self,
        parser: Optional[Any] = ...,
        builder: Optional[Any] = ...,
        name: Optional[Any] = ...,
        namespace: Optional[Any] = ...,
        prefix: Optional[Any] = ...,
        attrs: Optional[Any] = ...,
        parent: Optional[Any] = ...,
        previous: Optional[Any] = ...,
        is_xml: Optional[Any] = ...,
        sourceline: Optional[Any] = ...,
        sourcepos: Optional[Any] = ...,
        can_be_empty_element: Optional[Any] = ...,
        cdata_list_attributes: Optional[Any] = ...,
        preserve_whitespace_tags: Optional[Any] = ...,
    ) -> None: ...
    parserClass: Any = ...
    def __copy__(self): ...
    @property
    def is_empty_element(self): ...
    isSelfClosing: Any = ...
    @property
    def string(self): ...
    @string.setter
    def string(self, string: Any) -> None: ...
    strings: Any = ...
    @property
    def stripped_strings(self) -> None: ...
    def get_text(self, separator: str = ..., strip: bool = ..., types: Any = ...): ...
    getText: Any = ...
    text: Any = ...
    def decompose(self) -> None: ...
    def clear(self, decompose: bool = ...) -> None: ...
    def smooth(self) -> None: ...
    def index(self, element: Any): ...
    def get(self, key: Any, default: Optional[Any] = ...): ...
    def get_attribute_list(self, key: Any, default: Optional[Any] = ...): ...
    def has_attr(self, key: Any): ...
    def __hash__(self) -> Any: ...
    def __getitem__(self, key: Any): ...
    def __iter__(self) -> Any: ...
    def __len__(self): ...
    def __contains__(self, x: Any): ...
    def __bool__(self): ...
    def __setitem__(self, key: Any, value: Any) -> None: ...
    def __delitem__(self, key: Any) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any): ...
    def __getattr__(self, tag: Any): ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
    def __unicode__(self): ...
    def encode(
        self,
        encoding: Any = ...,
        indent_level: Optional[Any] = ...,
        formatter: str = ...,
        errors: str = ...,
    ): ...
    def decode(
        self,
        pretty_print: bool = ...,
        indent_level: Optional[Any] = ...,
        eventual_encoding: Any = ...,
        formatter: str = ...,
    ): ...
    def prettify(self, encoding: Optional[Any] = ..., formatter: str = ...): ...
    def decode_contents(
        self,
        indent_level: Optional[Any] = ...,
        eventual_encoding: Any = ...,
        formatter: str = ...,
    ): ...
    def encode_contents(
        self,
        indent_level: Optional[Any] = ...,
        encoding: Any = ...,
        formatter: str = ...,
    ): ...
    def renderContents(
        self,
        encoding: Any = ...,
        prettyPrint: bool = ...,
        indentLevel: int = ...,
    ): ...
    def find(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        recursive: bool = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findChild: Any = ...
    def find_all(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        recursive: bool = ...,
        text: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    findAll: Any = ...
    findChildren: Any = ...
    @property
    def children(self): ...
    @property
    def descendants(self) -> None: ...
    def select_one(self, selector: Any, namespaces: Optional[Any] = ..., **kwargs: Any): ...
    def select(
        self,
        selector: Any,
        namespaces: Optional[Any] = ...,
        limit: Optional[Any] = ...,
        **kwargs: Any,
    ): ...
    def childGenerator(self): ...
    def recursiveChildGenerator(self): ...
    def has_key(self, key: Any): ...

class SoupStrainer:
    name: Any = ...
    attrs: Any = ...
    text: Any = ...
    def __init__(
        self,
        name: Optional[Any] = ...,
        attrs: Any = ...,
        text: Optional[Any] = ...,
        **kwargs: Any,
    ) -> None: ...
    def search_tag(self, markup_name: Optional[Any] = ..., markup_attrs: Any = ...): ...
    searchTag: Any = ...
    def search(self, markup: Any): ...

class ResultSet(list):
    source: Any = ...
    def __init__(self, source: Any, result: Any = ...) -> None: ...
    def __getattr__(self, key: Any) -> None: ...
