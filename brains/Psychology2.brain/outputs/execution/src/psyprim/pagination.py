from __future__ import annotations
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import re

_ROMAN_RE = re.compile(r"^(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.I)
_LOCNUM_RE = re.compile(r"^(?P<prefix>.*?)(?P<num>\d+)$")


def roman_to_int(s: str) -> int:
    s = s.strip().upper()
    if not s or not _ROMAN_RE.match(s):
        raise ValueError(f"Invalid roman numeral: {s!r}")
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def _page_key(page: Union[int, str]) -> Tuple[int, int]:
    if isinstance(page, int):
        return (1, page)
    s = str(page).strip()
    if not s:
        raise ValueError("Empty page label")
    if s.isdigit():
        return (1, int(s))
    try:
        return (0, roman_to_int(s))
    except ValueError:
        return (2, hash(s))


def _parse_locnum(loc: str) -> Optional[Tuple[str, int]]:
    m = _LOCNUM_RE.match(loc.strip())
    if not m:
        return None
    return m.group("prefix"), int(m.group("num"))


@dataclass(frozen=True)
class PaginationEntry:
    print_start: Union[int, str]
    print_end: Union[int, str]
    loc_start: str
    loc_end: Optional[str] = None

    def __post_init__(self) -> None:
        if not str(self.loc_start).strip():
            raise ValueError("loc_start must be non-empty")
        if self.loc_end is not None and not str(self.loc_end).strip():
            raise ValueError("loc_end must be non-empty if provided")


@dataclass
class PaginationMapping:
    entries: List[PaginationEntry]
    edition_id: Optional[str] = None
    translation_id: Optional[str] = None

    def validate(self) -> None:
        if not self.entries:
            raise ValueError("Pagination mapping has no entries")
        ranges: List[Tuple[Tuple[int, int], Tuple[int, int], PaginationEntry]] = []
        for e in self.entries:
            ks, ke = _page_key(e.print_start), _page_key(e.print_end)
            if ks > ke:
                raise ValueError(f"Invalid page range: {e.print_start!r}..{e.print_end!r}")
            ranges.append((ks, ke, e))
        ranges.sort(key=lambda x: x[0])
        last_end: Optional[Tuple[int, int]] = None
        for ks, ke, e in ranges:
            if last_end is not None and ks <= last_end:
                raise ValueError(f"Overlapping/unsorted page ranges near {e.print_start!r}")
            last_end = ke
            if e.loc_end is not None:
                a, b = _parse_locnum(e.loc_start), _parse_locnum(e.loc_end)
                if not a or not b or a[0] != b[0] or b[1] < a[1]:
                    raise ValueError(f"Invalid loc range: {e.loc_start!r}..{e.loc_end!r}")
                if (ke[0], ke[1]) == (ks[0], ks[1]) and b[1] != a[1]:
                    raise ValueError("Single-page entry cannot have differing loc_start/loc_end")
        self.entries = [r[2] for r in ranges]

    def locator_for_print_page(self, page: Union[int, str]) -> str:
        k = _page_key(page)
        for e in self.entries:
            ks, ke = _page_key(e.print_start), _page_key(e.print_end)
            if ks <= k <= ke:
                if e.loc_end is None or k == ks:
                    return e.loc_start
                a, b = _parse_locnum(e.loc_start), _parse_locnum(e.loc_end)
                if not a or not b or a[0] != b[0]:
                    return e.loc_start
                offset = k[1] - ks[1]
                return f"{a[0]}{a[1] + offset}"
        raise KeyError(f"Print page not covered by mapping: {page!r}")

    def canonical_citation_locator(
        self,
        print_page: Union[int, str],
        *,
        digital_label: str = "loc",
        print_label: str = "p",
        sep: str = "; ",
    ) -> str:
        loc = self.locator_for_print_page(print_page)
        p = str(print_page).strip()
        return f"{print_label}. {p}{sep}{digital_label}. {loc}"


def mapping_from_obj(obj: Any) -> PaginationMapping:
    if isinstance(obj, PaginationMapping):
        obj.validate()
        return obj
    if not isinstance(obj, dict):
        raise TypeError("Pagination mapping must be a dict or PaginationMapping")
    entries_in = obj.get("entries") or obj.get("pages") or obj.get("mapping")
    if not isinstance(entries_in, list) or not entries_in:
        raise ValueError("Pagination mapping dict must include non-empty 'entries' (or pages/mapping) list")
    entries: List[PaginationEntry] = []
    for it in entries_in:
        if isinstance(it, dict):
            ps = it.get("print_start", it.get("print", it.get("page")))
            pe = it.get("print_end", ps)
            ls = it.get("loc_start", it.get("loc", it.get("locator")))
            le = it.get("loc_end")
        elif isinstance(it, (list, tuple)) and len(it) in (2, 4):
            ps, ls = it[0], it[1]
            pe, le = (it[2], it[3]) if len(it) == 4 else (ps, None)
        else:
            raise ValueError(f"Invalid entry: {it!r}")
        if ps is None or ls is None:
            raise ValueError(f"Entry missing print/loc: {it!r}")
        entries.append(PaginationEntry(ps, pe, str(ls), str(le) if le is not None else None))
    m = PaginationMapping(entries=entries, edition_id=obj.get("edition_id"), translation_id=obj.get("translation_id"))
    m.validate()
    return m
