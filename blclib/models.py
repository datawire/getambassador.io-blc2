from typing import NamedTuple, Optional
from urllib.parse import urljoin, urlparse

import bs4.element


class URLReference:
    base: Optional['URLReference']
    ref: str
    _resolved: Optional[str]

    @property
    def resolved(self) -> str:
        if self._resolved:
            return self._resolved
        if urlparse(self.ref).scheme:
            return self.ref
        if not self.base:
            raise Exception(
                f"could not resolve URL reference: {self.ref}: is relative, and have no base for it to be relative to"
            )
        ret = urljoin(self.base.resolved, self.ref)
        if not urlparse(ret).scheme:
            raise Exception(f"could not resolve URL reference: {ret}")
        return ret

    def __init__(
        self,
        ref: str,
        base: Optional['URLReference'] = None,
        resolved: Optional[str] = None,
    ):
        self.ref = ref
        self.base = base
        self._resolved = resolved

    def parse(self, ref: str) -> 'URLReference':
        return URLReference(ref, base=self)

    def _replace(
        self,
        base: Optional['URLReference'] = None,
        ref: Optional[str] = None,
        resolved: Optional[str] = None,
    ) -> 'URLReference':
        return URLReference(
            base=(base or self.base),
            ref=(ref or self.ref),
            resolved=(resolved or self.resolved),
        )

    def __repr__(self) -> str:
        parts = [f'ref={self.ref}']
        if self.base:
            parts += [f'base={self.base}']
        if self._resolved:
            parts += [f'resolved={self._resolved}']
        return f'URLReference({", ".join(parts)})'

    def __hash__(self) -> int:
        return (self.base, self.ref, self._resolved).__hash__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, URLReference):
            return (
                self.base == other.base
                and self.ref == other.ref
                and self.resolved == other.resolved
            )
        return False


class Link(NamedTuple):
    linkurl: URLReference
    pageurl: URLReference
    html: Optional[bs4.element.Tag]
