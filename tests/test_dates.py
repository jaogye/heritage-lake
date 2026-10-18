import pytest

from lake.dates import DateRange, parse_date


@pytest.mark.parametrize(
    "text, expected",
    [
        ("+1432-01-01T00:00:00Z", (1432, 1432, False)),
        ("1562-01-01T00:00:00Z", (1562, 1562, False)),
        ("1562", (1562, 1562, False)),
        ("ca. 1560", (1555, 1565, True)),
        ("c.1890", (1885, 1895, True)),
        ("omstreeks 1640", (1635, 1645, True)),
        ("vers 1460", (1455, 1465, True)),
        ("ca. 1495-1505", (1495, 1505, True)),
        ("1610–1611", (1610, 1611, False)),
        ("1612-14", (1612, 1614, False)),
        ("1520s", (1520, 1529, True)),
        ("vóór 1489", (1464, 1489, True)),
        ("before 1600", (1575, 1600, True)),
        ("après 1700", (1700, 1725, True)),
        ("16th century", (1500, 1599, True)),
        ("16de eeuw", (1500, 1599, True)),
        ("XVIe siècle", (1500, 1599, True)),
        ("late 15th century", (1467, 1499, True)),
        ("tweede helft 17de eeuw", (1650, 1699, True)),
        ("early 20th century", (1900, 1932, True)),
        ("1562 or 1563", (1562, 1563, True)),
    ],
)
def test_parse(text, expected):
    d = parse_date(text)
    assert (d.start, d.end, d.approx) == expected


@pytest.mark.parametrize("text", [None, "", "undated", "z.d.", "inv. 12"])
def test_unparseable(text):
    assert parse_date(text) is None


def test_overlap():
    assert DateRange(1555, 1565, True).overlaps(DateRange(1562, 1562, False))
    assert not DateRange(1610, 1611, False).overlaps(DateRange(1612, 1614, False))
