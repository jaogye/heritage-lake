import pytest

from lake.institutions import resolve_institution
from lake.names import keys_match, parse_creator


@pytest.mark.parametrize(
    "raw, name, role, key",
    [
        ("Bruegel, Pieter (I)", "Pieter Bruegel the Elder", "author", "bruegel"),
        ("Bruegel de Oude, Pieter", "Pieter Bruegel the Elder", "author", "bruegel"),
        ("Pieter Brueghel the Younger", "Pieter Brueghel the Younger", "author", "bruegel"),
        (
            "toegeschreven aan Pieter Bruegel (I)",
            "Pieter Bruegel the Elder",
            "attributed",
            "bruegel",
        ),
        ("Workshop of Rogier van der Weyden", "Rogier van der Weyden", "workshop", "weyden"),
        ("David, Jacques-Louis (1748-1825)", "Jacques-Louis David", "author", "david"),
        ("Rysselberghe, Théo van", "Théo van Rysselberghe", "author", "ryselberge"),
        ("Hans Memlinc", "Hans Memlinc", "author", "memlinc"),
        ("Jheronimus Bosch", "Jheronimus Bosch", "author", "bosch"),
    ],
)
def test_parse_creator(raw, name, role, key):
    c = parse_creator(raw)
    assert (c.name, c.role, c.key) == (name, role, key)


@pytest.mark.parametrize("raw", ["Anoniem (Brugge)", "Unknown Flemish master", "anonyme"])
def test_anonymous(raw):
    c = parse_creator(raw)
    assert c.role == "anonymous" and c.name is None and c.key is None


def test_uri_and_empty_ignored():
    assert parse_creator("http://data.europeana.eu/agent/123") is None
    assert parse_creator("  ") is None


def test_key_variants_match():
    assert keys_match(parse_creator("Hans Memling").key, parse_creator("Hans Memlinc").key)
    assert not keys_match(parse_creator("Gerard David").key, parse_creator("Jan van Eyck").key)


@pytest.mark.parametrize(
    "raw, canonical",
    [
        ("KMSKB", "Royal Museums of Fine Arts of Belgium"),
        ("Musées royaux des Beaux-Arts de Belgique", "Royal Museums of Fine Arts of Belgium"),
        ("Musea Brugge – Groeningemuseum", "Groeningemuseum"),
        ("musea brugge - groeningemuseum", "Groeningemuseum"),
        ("Onze-Lieve-Vrouwekathedraal Antwerpen", "Cathedral of Our Lady (Antwerp)"),
        ("Royal Museums of Fine Art of Belgium", "Royal Museums of Fine Arts of Belgium"),  # fuzzy
    ],
)
def test_institutions(raw, canonical):
    name, _, known = resolve_institution(raw)
    assert known and name == canonical


def test_unknown_institution_passes_through():
    assert resolve_institution("Museum van Deinze en de Leiestreek") == (
        "Museum van Deinze en de Leiestreek",
        None,
        False,
    )
