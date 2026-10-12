"""Record and record-set classes in the style of odoo-sdk.

A set is created with the credentials, filled by one of its ``get...`` methods,
and then read like a list::

    transactions = TransactionSet(yuki_cred)
    transactions.get(START, END)
    print(transactions.count)
    for transaction in transactions:
        print(transaction.amount)

A record holds one value and is filled by ``get`` or ``read``. Its fields are
declared on the class, like the fields of an odoo-sdk record, and set as
attributes when it is filled::

    period = Period(yuki_cred)
    period.get(2026)
    print(period.start, period.end)

The administration is ``admin_id`` of the credentials unless
``administration_id`` is passed. Every ``get`` replaces the previous content.
The SOAP call sits on the service class in the same module.
"""

from __future__ import annotations

import dataclasses
from typing import Generic, Iterable, Iterator, TypeVar, overload

from .clientcredentials import ClientCredentials
from .exceptions import YukiConfigError
from .parsing import to_jsonable

Row = TypeVar("Row")


class _Yuki:
    """Credentials and the administration a record or set reads from."""

    def __init__(self, client_credentials: ClientCredentials, administration_id: str | None = None):
        self.client_credentials = client_credentials
        self._administration_id = administration_id

    @property
    def administration_id(self) -> str:
        """The administration passed in, otherwise ``admin_id`` of the credentials."""

        selected = str(self._administration_id or getattr(self.client_credentials, "admin_id", "") or "").strip()
        if not selected:
            raise YukiConfigError(
                f"{type(self).__name__} needs an administration: pass administration_id or fill admin_id in the credentials"
            )
        return selected


class YukiRecordSet(_Yuki, Generic[Row]):
    """A list of rows read from Yuki."""

    def __init__(self, client_credentials: ClientCredentials, administration_id: str | None = None):
        super().__init__(client_credentials, administration_id)
        self._record_set: list[Row] = []

    def __iter__(self) -> Iterator[Row]:
        return iter(self._record_set)

    @overload
    def __getitem__(self, item: int) -> Row: ...

    @overload
    def __getitem__(self, item: slice) -> list[Row]: ...

    def __getitem__(self, item):
        return self._record_set[item]

    def __len__(self) -> int:
        return len(self._record_set)

    def __bool__(self) -> bool:
        return bool(self._record_set)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} count={self.count}>"

    @property
    def count(self) -> int:
        return len(self._record_set)

    def to_json(self) -> list:
        """The rows as JSON-ready dicts."""

        return [_to_json(row) for row in self._record_set]

    def _fill(self, rows: Iterable[Row]) -> None:
        self._record_set = list(rows)


class YukiRecord(_Yuki):
    """One value read from Yuki.

    Subclasses declare the fields of their value as class annotations; filling
    the record copies those fields onto it as attributes.
    """

    _value = None

    def __getattr__(self, name):
        # Only called for a name that is not set: a declared field before get() or read().
        if not name.startswith("_") and name in _declared_fields(type(self)):
            raise AttributeError(f"{type(self).__name__} is empty: call get() or read() first (looking up {name!r})")
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __bool__(self) -> bool:
        return self._value is not None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._value!r}>"

    @property
    def value(self):
        """The parsed value itself (a dataclass), or ``None`` before ``get``."""

        return self._value

    def to_json(self):
        return _to_json(self._value)

    def _set(self, value) -> None:
        self._value = value
        for name in _declared_fields(type(self)):
            if isinstance(getattr(type(self), name, None), property):
                continue
            if value is None:
                self.__dict__.pop(name, None)
            else:
                setattr(self, name, getattr(value, name))


def _declared_fields(cls) -> list[str]:
    """Field names annotated on the record classes, without the private ones."""

    names: list[str] = []
    for klass in reversed(cls.__mro__):
        for name in vars(klass).get("__annotations__", {}):
            if not name.startswith("_") and name not in names:
                names.append(name)
    return names


def _to_json(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {item.name: getattr(value, item.name) for item in dataclasses.fields(value)}
    return to_jsonable(value)
