"""Turn Yuki responses into one plain shape, and read values from it.

Typed operations come back from zeep as objects; untyped (``<any>``) operations
come back as lxml elements, sometimes wrapped in a zeep object. :func:`plain`
turns all of them into dicts, lists, and scalars. Every parser in this package
reads that shape, so one parser handles a live zeep result, an lxml element,
and a stored JSON snapshot alike.

Field lookup with :func:`get` is exact first, then case-insensitive: Yuki's
casing differs between operations (``EmailWork`` / ``EMailWork``, ``hID`` /
``HID``) and is not documented for the untyped responses.

This module has no dependency on the rest of the package.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Callable, Hashable, Iterator, TypeVar

from lxml import etree

Row = TypeVar("Row")


def plain(value):
    """Return ``value`` as dicts, lists, and scalars.

    zeep objects are serialised. An lxml element becomes ``{name: value}`` with
    its attributes under their own name (``"ID"``) and repeated children as a
    list; an element with text and attributes keeps the text under ``"_text"``;
    a leaf element becomes its text.
    """

    if value is None:
        return None
    if isinstance(value, etree._Element):
        return _element_to_plain(value)
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if hasattr(value, "__values__"):  # zeep CompoundValue
        from zeep.helpers import serialize_object

        return plain(serialize_object(value, target_cls=dict))
    return value


def _element_to_plain(element):
    children = [item for item in element if isinstance(item.tag, str)]
    attributes = {etree.QName(key).localname: value for key, value in element.attrib.items()}
    text_value = element.text.strip() if element.text and element.text.strip() else None
    if not children and not attributes:
        return text_value
    result: dict = dict(attributes)
    for item in children:
        name = local_name(item)
        value = _element_to_plain(item)
        if name in result and name not in attributes:
            if not isinstance(result[name], list):
                result[name] = [result[name]]
            result[name].append(value)
        else:
            result[name] = value
    if text_value is not None and not children:
        result["_text"] = text_value
    return result


def local_name(element) -> str:
    return etree.QName(element).localname


def unwrap_rows(value, row_name: str) -> list:
    """Return the ``row_name`` items of a response, as plain values.

    Handles a list of rows, an array wrapper (``{row_name: [...]}``), a single
    row, and rows nested deeper (``{"Documents": {"Document": [...]}}``).
    """

    data = plain(value)
    if data is None:
        return []
    if isinstance(data, list):
        rows = []
        for item in data:
            if isinstance(item, dict) and set(item) == {row_name}:
                rows.extend(unwrap_rows(item[row_name], row_name))
            else:
                rows.append(item)
        return rows
    if isinstance(data, dict):
        if row_name in data:
            inner = data[row_name]
            if inner is None:
                return []
            return inner if isinstance(inner, list) else [inner]
        for item in data.values():
            if isinstance(item, (dict, list)):
                found = unwrap_rows(item, row_name)
                if found:
                    return found
    return []


def first_rows(value, *row_names: str) -> list:
    """Return the rows of the first ``row_names`` entry that has any."""

    for name in row_names:
        rows = unwrap_rows(value, name)
        if rows:
            return rows
    return []


def get(data, *names):
    """Return the first non-empty value for ``names`` in a plain dict."""

    if not isinstance(data, dict):
        return None
    lowered = None
    for name in names:
        value = data.get(name)
        if value is not None:
            return value
        if lowered is None:
            lowered = {str(key).lower(): item for key, item in data.items()}
        value = lowered.get(name.lower())
        if value is not None:
            return value
    return None


def to_text(value) -> str | None:
    """Return stripped text, or ``None`` for an empty value. Reads ``"_text"`` of a dict."""

    if isinstance(value, dict):
        value = value.get("_text")
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def to_decimal(value) -> Decimal | None:
    if not isinstance(value, (Decimal, int, float)):
        value = to_text(value)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def to_amount(value) -> Decimal | None:
    """Return an amount that Yuki sends as text, in either notation.

    ``1234.56``, ``1234,56``, ``1.234,56`` and ``1,234.56`` all give 1234.56:
    the last separator is the decimal one.
    """

    if isinstance(value, (Decimal, int, float)):
        return Decimal(str(value))
    text_value = to_text(value)
    if text_value is None:
        return None
    text_value = text_value.replace(" ", "").replace("\u00a0", "")
    if "," in text_value and "." in text_value:
        if text_value.rfind(",") > text_value.rfind("."):
            text_value = text_value.replace(".", "").replace(",", ".")
        else:
            text_value = text_value.replace(",", "")
    elif "," in text_value:
        text_value = text_value.replace(",", ".")
    return to_decimal(text_value)


def to_int(value) -> int | None:
    number = to_decimal(value)
    return int(number) if number is not None else None


def to_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    value = to_text(value)
    if value is None:
        return None
    return value.lower() in {"true", "1"}


# Untyped responses write dates as text, not always ISO: contacts carry
# ``10/08/2026 16:35:39`` for 8 October 2026 (seen live), month first.
_TEXT_DATE_FORMATS = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y")


def _parse_date_text(text_value: str) -> datetime:
    try:
        return datetime.fromisoformat(text_value.replace("Z", "+00:00"))
    except ValueError:
        pass
    for date_format in _TEXT_DATE_FORMATS:
        try:
            return datetime.strptime(text_value, date_format)
        except ValueError:
            continue
    raise ValueError(f"Unknown Yuki date format: {text_value!r}")


def to_date(value) -> date | None:
    """Return the date part of a Yuki date or dateTime. ``0001-01-01`` is no date."""

    if isinstance(value, datetime):
        result = value.date()
    elif isinstance(value, date):
        result = value
    else:
        text_value = to_text(value)
        if text_value is None:
            return None
        result = _parse_date_text(text_value).date()
    return None if result.year <= 1 else result


def to_datetime(value) -> datetime | None:
    """Return a Yuki dateTime. ``0001-01-01`` is no date."""

    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime(value.year, value.month, value.day)
    else:
        text_value = to_text(value)
        if text_value is None:
            return None
        result = _parse_date_text(text_value)
    return None if result.year <= 1 else result


def to_bytes(value) -> bytes | None:
    """Return binary content; a string is read as base64."""

    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    text_value = to_text(value)
    return base64.b64decode(text_value) if text_value else None


def to_jsonable(value):
    """Return ``value`` in a form ``json.dump`` accepts, for storing raw responses.

    Decimals become strings, dates ISO strings, bytes ``{"_base64": ...}``, and
    lxml elements ``{"_xml": ...}`` with their XML.
    """

    if isinstance(value, etree._Element):
        return {"_xml": etree.tostring(value, encoding="unicode")}
    if isinstance(value, (bytes, bytearray)):
        return {"_base64": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "__values__"):
        return to_jsonable(plain(value))
    return value


def iter_unique_pages(
    read_page: Callable[[int], list[Row]],
    *,
    first: int,
    page_size: int,
    next_position: Callable[[int, list[Row]], int],
    key: Callable[[Row], Hashable] = lambda row: row.id,
    max_pages: int | None = None,
) -> Iterator[Row]:
    """Yield the rows of a paged read, each key once.

    ``read_page(position)`` returns one page; ``next_position`` gives the next
    position (a record offset or a page number). Stops on an empty page, a
    short page, a page with no new keys, or after ``max_pages``. The "no new
    keys" stop protects against a read that ignores its paging parameter.
    """

    seen: set = set()
    position = first
    pages = 0
    while max_pages is None or pages < max_pages:
        page = read_page(position)
        pages += 1
        fresh = [row for row in page if key(row) not in seen]
        for row in fresh:
            seen.add(key(row))
            yield row
        if not fresh or len(page) < page_size:
            return
        position = next_position(position, page)
