from datetime import date, datetime
from decimal import Decimal

from lxml import etree
from zeep import xsd

from yuki_sdk.parsing import (
    first_rows,
    get,
    iter_unique_pages,
    plain,
    to_amount,
    to_bytes,
    to_date,
    to_datetime,
    to_decimal,
    to_text,
    unwrap_rows,
)
from yuki_sdk.soap import parse_domains


def test_plain_reads_attributes_text_and_repeated_children():
    element = etree.fromstring(
        '<Items><Item ID="1"><Type ID="6">Verkoopfactuur</Type><Tag>a</Tag><Tag>b</Tag><Empty/></Item></Items>'
    )

    assert plain(element) == {
        "Item": {"ID": "1", "Type": {"ID": "6", "_text": "Verkoopfactuur"}, "Tag": ["a", "b"], "Empty": None}
    }


def test_plain_serialises_zeep_objects_and_wrapped_any_content():
    inner = xsd.ComplexType([xsd.Element("code", xsd.String())])
    outer = xsd.ComplexType([xsd.Element("rows", inner, max_occurs="unbounded")])
    value = outer(rows=[inner(code="A"), inner(code="B")])

    assert plain(value) == {"rows": [{"code": "A"}, {"code": "B"}]}
    # An untyped result as zeep returns it: the lxml content under _value_1.
    wrapped = {"_value_1": etree.fromstring('<Domains><Domain ID="d-1"><Name>x</Name></Domain></Domains>')}
    assert unwrap_rows(wrapped, "Domain") == [{"ID": "d-1", "Name": "x"}]


def test_unwrap_rows_shapes():
    assert unwrap_rows(None, "Row") == []
    assert unwrap_rows([{"id": 1}, {"id": 2}], "Row") == [{"id": 1}, {"id": 2}]
    assert unwrap_rows({"Row": [{"id": 1}]}, "Row") == [{"id": 1}]
    assert unwrap_rows({"Row": {"id": 1}}, "Row") == [{"id": 1}]
    assert unwrap_rows({"Outer": {"Row": {"id": 1}}}, "Row") == [{"id": 1}]
    assert unwrap_rows([{"Row": [{"id": 1}]}], "Row") == [{"id": 1}]
    assert first_rows({"Folder": [{"id": 1}]}, "DocumentFolder", "Folder") == [{"id": 1}]


def test_get_is_exact_first_then_case_insensitive():
    data = {"EmailWork": "a@b.be", "emailwork": "other", "Empty": None, "hID": "7"}

    assert get(data, "EmailWork") == "a@b.be"
    assert get(data, "EMailWork") in {"a@b.be", "other"}
    assert get(data, "HID") == "7"
    assert get(data, "Empty", "hID") == "7"
    assert get("not a dict", "x") is None


def test_value_conversions():
    assert to_text("  x ") == "x"
    assert to_text("   ") is None
    assert to_text({"_text": "y", "ID": "1"}) == "y"
    assert to_decimal("12.50") == Decimal("12.50")
    assert to_decimal("n/a") is None
    assert to_date("2026-10-08T00:00:00") == date(2026, 10, 8)
    assert to_date("0001-01-01T00:00:00") is None
    assert to_datetime(datetime(1, 1, 1)) is None
    assert to_datetime("2026-10-08T09:30:00Z").hour == 9
    assert to_bytes("JVBERg==") == b"%PDF"
    assert to_bytes(b"raw") == b"raw"
    assert to_amount("1.234,56") == Decimal("1234.56")
    assert to_amount("1,234.56") == Decimal("1234.56")
    assert to_amount("-10,5") == Decimal("-10.5")
    assert to_amount("12.50") == Decimal("12.50")
    assert to_amount("") is None


def test_text_dates_from_untyped_responses_are_month_first():
    # Contact Created/Modified as Yuki sent them for 8 October 2026.
    assert to_datetime("10/08/2026 16:35:39") == datetime(2026, 10, 8, 16, 35, 39)
    assert to_date("10/08/2026 16:35:39") == date(2026, 10, 8)
    assert to_date("2026-10-08") == date(2026, 10, 8)


class _Row:
    def __init__(self, id):
        self.id = id


def test_iter_unique_pages_stops_on_short_page_and_repeats():
    rows = [_Row(n) for n in range(5)]
    calls = []

    def read(position):
        calls.append(position)
        return rows[position : position + 2]

    result = list(iter_unique_pages(read, first=0, page_size=2, next_position=lambda p, page: p + len(page)))

    assert [row.id for row in result] == [0, 1, 2, 3, 4]
    assert calls == [0, 2, 4]

    repeating = list(iter_unique_pages(lambda p: rows[:2], first=1, page_size=2, next_position=lambda p, page: p + 1))
    assert [row.id for row in repeating] == [0, 1]


def test_parse_domains_reads_status():
    domains = parse_domains(
        etree.fromstring('<Domains><Domain ID="d-1"><Name>curlo-test</Name><Status ID="0">Active</Status></Domain></Domains>')
    )

    assert domains[0].id == "d-1"
    assert domains[0].status == "Active"
    assert domains[0].status_id == "0"
