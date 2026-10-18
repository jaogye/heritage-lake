"""Generate the synthetic sample raw zone and in-house catalogue in data/sample/.

The records imitate the *shape and messiness* of real Wikidata, Europeana and
museum-website records for well-known works in Belgian collections: titles in
English/Dutch/French, inverted creator names, attribution qualifiers, inventory
numbers written three ways, the same object served twice by two aggregators,
unknown institutions, a record that changed between two harvests.

Identifiers (QIDs, Europeana ids, inventory numbers) and image URLs are
placeholders, not real catalogue data. Run `heritage-harvest` for real records.

    python scripts/make_sample_data.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "sample"
D1, D2 = "2026-10-01T08:00:00+00:00", "2026-10-08T08:00:00+00:00"
PDM = "http://creativecommons.org/publicdomain/mark/1.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
INC = "http://rightsstatements.org/vocab/InC/1.0/"


def h(payload):
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def rec(source, sid, url, payload, fetched=D1):
    return {
        "source": source,
        "source_id": sid,
        "url": url,
        "fetched_at": fetched,
        "payload": payload,
        "content_hash": h(payload),
    }


def commons(name):
    return f"http://commons.wikimedia.org/wiki/Special:FilePath/{name}"


# (qid, label, description, type, creators, inception, collection, inventory, materials, depicts, image)
WIKIDATA = [
    (
        "Q9000001",
        "Adoration of the Mystic Lamb",
        "polyptych by Hubert and Jan van Eyck",
        "altarpiece",
        ["Hubert van Eyck", "Jan van Eyck"],
        "1432",
        "St Bavo's Cathedral",
        None,
        ["oil paint", "oak panel"],
        ["Lamb of God", "angel", "Adam", "Eve"],
        "Ghent_Altarpiece_fixture.jpg",
    ),
    (
        "Q9000002",
        "The Fall of the Rebel Angels",
        "painting by Pieter Bruegel the Elder",
        "painting",
        ["Pieter Bruegel the Elder"],
        "1562",
        "Royal Museums of Fine Arts of Belgium",
        "584",
        ["oil paint", "oak panel"],
        ["Archangel Michael", "angel", "demon"],
        "Rebel_Angels_fixture.jpg",
    ),
    (
        "Q9000003",
        "Landscape with the Fall of Icarus",
        "painting attributed to Pieter Bruegel the Elder",
        "painting",
        ["Pieter Bruegel the Elder"],
        "1560",
        "Royal Museums of Fine Arts of Belgium",
        "4030",
        ["oil paint", "canvas"],
        ["Icarus", "ploughman", "ship", "sea"],
        "Icarus_fixture.jpg",
    ),
    (
        "Q9000004",
        "The Census at Bethlehem",
        "painting by Pieter Bruegel the Elder",
        "painting",
        ["Pieter Bruegel the Elder"],
        "1566",
        "Royal Museums of Fine Arts of Belgium",
        "3637",
        ["oil paint", "oak panel"],
        ["Mary", "Joseph", "snow", "village"],
        "Census_fixture.jpg",
    ),
    (
        "Q9000005",
        "The Death of Marat",
        "painting by Jacques-Louis David",
        "painting",
        ["Jacques-Louis David"],
        "1793",
        "Royal Museums of Fine Arts of Belgium",
        "3260",
        ["oil paint", "canvas"],
        ["Jean-Paul Marat", "bathtub", "death"],
        "Marat_fixture.jpg",
    ),
    (
        "Q9000006",
        "Madonna with Canon van der Paele",
        "painting by Jan van Eyck",
        "painting",
        ["Jan van Eyck"],
        "1436",
        "Groeningemuseum",
        "0000.GRO0161.I",
        ["oil paint", "oak panel"],
        ["Virgin Mary", "Child Jesus", "Saint George", "Saint Donatian"],
        "Van_der_Paele_fixture.jpg",
    ),
    (
        "Q9000007",
        "The Last Judgment",
        "triptych by Hieronymus Bosch",
        "triptych",
        ["Hieronymus Bosch"],
        "1500",
        "Groeningemuseum",
        "0000.GRO0208.I",
        ["oil paint", "oak panel"],
        ["Last Judgment", "hell", "paradise"],
        "Bosch_Last_Judgment_fixture.jpg",
    ),
    (
        "Q9000008",
        "Moreel Triptych",
        "triptych by Hans Memling",
        "triptych",
        ["Hans Memling"],
        "1484",
        "Groeningemuseum",
        "0000.GRO0239.I",
        ["oil paint", "oak panel"],
        ["Saint Christopher", "Willem Moreel", "donor portrait"],
        "Moreel_fixture.jpg",
    ),
    (
        "Q9000009",
        "Shrine of Saint Ursula",
        "reliquary by Hans Memling",
        "reliquary",
        ["Hans Memling"],
        "1489",
        "Memling Museum (St John's Hospital)",
        "O.SJ0176.I",
        ["oil paint", "gilded oak"],
        ["Saint Ursula", "martyrdom", "Cologne"],
        "Ursula_Shrine_fixture.jpg",
    ),
    (
        "Q9000010",
        "Madonna of Bruges",
        "marble sculpture by Michelangelo",
        "sculpture",
        ["Michelangelo"],
        "1504",
        "Church of Our Lady (Bruges)",
        None,
        ["Carrara marble"],
        ["Virgin Mary", "Child Jesus"],
        "Madonna_of_Bruges_fixture.jpg",
    ),
    (
        "Q9000011",
        "The Elevation of the Cross",
        "triptych by Peter Paul Rubens",
        "triptych",
        ["Peter Paul Rubens"],
        "1610",
        "Cathedral of Our Lady (Antwerp)",
        None,
        ["oil paint", "panel"],
        ["crucifixion", "Jesus Christ"],
        "Elevation_fixture.jpg",
    ),
    (
        "Q9000012",
        "The Descent from the Cross",
        "triptych by Peter Paul Rubens",
        "triptych",
        ["Peter Paul Rubens"],
        "1612",
        "Cathedral of Our Lady (Antwerp)",
        None,
        ["oil paint", "panel"],
        ["deposition", "Jesus Christ", "Mary Magdalene"],
        "Descent_fixture.jpg",
    ),
    (
        "Q9000013",
        "Dulle Griet",
        "painting by Pieter Bruegel the Elder",
        "painting",
        ["Pieter Bruegel the Elder"],
        "1563",
        "Museum Mayer van den Bergh",
        "MMB.0045",
        ["oil paint", "oak panel"],
        ["Mad Meg", "hell", "demon"],
        "Dulle_Griet_fixture.jpg",
    ),
    (
        "Q9000014",
        "The Intrigue",
        "painting by James Ensor",
        "painting",
        ["James Ensor"],
        "1890",
        "Royal Museum of Fine Arts Antwerp",
        "2073",
        ["oil paint", "canvas"],
        ["mask", "carnival"],
        "Intrigue_fixture.jpg",
    ),
    (
        "Q9000015",
        "Memories",
        "painting by Fernand Khnopff",
        "painting",
        ["Fernand Khnopff"],
        "1889",
        "Royal Museums of Fine Arts of Belgium",
        "6162",
        ["pastel", "paper"],
        ["woman", "tennis"],
        "Memories_fixture.jpg",
    ),
    (
        "Q9000016",
        "The Caress",
        "painting by Fernand Khnopff",
        "painting",
        ["Fernand Khnopff"],
        "1896",
        "Royal Museums of Fine Arts of Belgium",
        "6768",
        ["oil paint", "canvas"],
        ["sphinx", "leopard"],
        "Caress_fixture.jpg",
    ),
    (
        "Q9000017",
        "The Empire of Light",
        "painting by René Magritte",
        "painting",
        ["René Magritte"],
        "1954",
        "Royal Museums of Fine Arts of Belgium",
        "6715",
        ["oil paint", "canvas"],
        ["house", "night", "sky", "street lamp"],
        "Empire_of_Light_fixture.jpg",
    ),
    (
        "Q9000018",
        "Portrait of Marguerite van Mons",
        "painting by Théo van Rysselberghe",
        "painting",
        ["Théo van Rysselberghe"],
        "1886",
        "Museum of Fine Arts Ghent",
        "1985-B",
        ["oil paint", "canvas"],
        ["girl", "portrait", "door"],
        "Marguerite_van_Mons_fixture.jpg",
    ),
    (
        "Q9000019",
        "The Judgement of Cambyses",
        "diptych by Gerard David",
        "diptych",
        ["Gerard David"],
        "1498",
        "Groeningemuseum",
        "0000.GRO0040.I",
        ["oil paint", "oak panel"],
        ["Cambyses II", "Sisamnes", "justice"],
        "Cambyses_fixture.jpg",
    ),
    (
        "Q9000020",
        "The King Drinks",
        "painting by Jacob Jordaens",
        "painting",
        ["Jacob Jordaens"],
        "1640",
        "Royal Museums of Fine Arts of Belgium",
        "3545",
        ["oil paint", "canvas"],
        ["feast", "Epiphany", "bean king"],
        "King_Drinks_fixture.jpg",
    ),
    (
        "Q9000021",
        "As the Old Sang, So the Young Pipe",
        "painting by Jacob Jordaens",
        "painting",
        ["Jacob Jordaens"],
        "1638",
        "Royal Museum of Fine Arts Antwerp",
        "677",
        ["oil paint", "canvas"],
        ["family", "music", "proverb"],
        "Old_Sang_fixture.jpg",
    ),
    (
        "Q9000022",
        "Portrait of Anthony of Burgundy",
        "painting by Rogier van der Weyden",
        "painting",
        ["Rogier van der Weyden"],
        "1460",
        "Royal Museums of Fine Arts of Belgium",
        "1453",
        ["oil paint", "oak panel"],
        ["Anthony of Burgundy", "arrow", "Order of the Golden Fleece"],
        "Anthony_of_Burgundy_fixture.jpg",
    ),
]


def wikidata_records():
    out = []
    for i, (q, label, desc, typ, creators, year, coll, inv, mats, deps, img) in enumerate(WIKIDATA):
        p = {
            "qid": q,
            "itemLabel": label,
            "itemDescription": desc,
            "inception": f"{year}-01-01T00:00:00Z",
            "image": commons(img),
            "type": [{"qid": f"Q97{i:03d}", "label": typ}],
            "creator": [{"qid": f"Q98{i:02d}{j}", "label": c} for j, c in enumerate(creators)],
            "collection": [{"qid": f"Q99{i:03d}", "label": coll}],
            "location": [],
            "material": [{"qid": f"Q96{i:02d}{j}", "label": m} for j, m in enumerate(mats)],
            "depicts": [{"qid": f"Q95{i:02d}{j}", "label": d} for j, d in enumerate(deps)],
        }
        if inv:
            p["inventory"] = inv
        out.append(rec("wikidata", q, f"https://www.wikidata.org/wiki/{q}", p))
    return out


def eu(eid, title, lang, creators, year, provider, ident=None, rights=INC, desc=None, dctype=None):
    p = {
        "id": eid,
        "guid": f"https://www.europeana.eu/item{eid}",
        "type": "IMAGE",
        "title": [title],
        "dcTitleLangAware": {lang: [title]},
        "dcCreator": creators,
        "year": [year],
        "dataProvider": [provider],
        "provider": ["Europeana Foundation"],
        "edmIsShownBy": [f"https://images.example.org/europeana{eid}.jpg"],
        "edmPreview": [f"https://api.europeana.eu/thumbnail/v2/url.json?uri=placeholder{eid}"],
        "rights": [rights],
        "country": ["belgium"],
    }
    if ident:
        p["dcIdentifier"] = [ident]
    if desc:
        p["dcDescription"] = [desc]
    if dctype:
        p["dcType"] = [dctype]
    return rec("europeana", eid, p["guid"], p)


def europeana_records():
    return [
        eu(
            "/2048128/BE_1",
            "Het Lam Gods",
            "nl",
            ["Eyck, Hubert van", "Eyck, Jan van"],
            "1432",
            "Sint-Baafskathedraal Gent",
            desc="Veelluik met de aanbidding van het Lam Gods.",
        ),
        eu(
            "/2048128/BE_2",
            "De val van de opstandige engelen",
            "nl",
            ["Bruegel, Pieter (I)"],
            "1562",
            "Royal Museums of Fine Arts of Belgium",
            "inv. 584",
        ),
        # same painting again, delivered by a second aggregator with French metadata
        eu(
            "/9200579/FR_2",
            "La Chute des anges rebelles",
            "fr",
            ["Bruegel l'Ancien, Pieter"],
            "1562",
            "Musées royaux des Beaux-Arts de Belgique",
            "Inv. 0584",
            rights=PDM,
            desc="<p>Saint Michel et les anges chassent les anges rebelles du ciel.</p>",
        ),
        eu(
            "/2048128/BE_3",
            "Landschap met de val van Icarus",
            "nl",
            ["toegeschreven aan Pieter Bruegel (I)"],
            "ca. 1560",
            "KMSKB",
            "inv. 4030",
            rights=PDM,
        ),
        eu(
            "/2048128/BE_4",
            "De volkstelling te Bethlehem",
            "nl",
            ["Bruegel, Pieter (I)"],
            "1566",
            "Royal Museums of Fine Arts of Belgium",
        ),
        eu(
            "/9200579/FR_5",
            "Marat assassiné",
            "fr",
            ["David, Jacques-Louis (1748-1825)"],
            "1793",
            "Musées royaux des Beaux-Arts de Belgique",
            "3260",
            rights=PDM,
        ),
        eu(
            "/2048128/BE_8",
            "Triptiek van Willem Moreel",
            "nl",
            ["Memling, Hans"],
            "1484",
            "Musea Brugge",
            "0000.GRO0239.I",
        ),
        eu(
            "/2048128/BE_11",
            "De kruisoprichting",
            "nl",
            ["Rubens, Peter Paul"],
            "1610-1611",
            "Onze-Lieve-Vrouwekathedraal Antwerpen",
        ),
        eu(
            "/2048128/BE_12",
            "The Descent from the Cross",
            "en",
            ["Rubens, Peter Paul"],
            "1612-14",
            "Onze-Lieve-Vrouwekathedraal Antwerpen",
        ),
        eu(
            "/2048128/BE_13",
            "Dulle Griet",
            "nl",
            ["Bruegel de Oude, Pieter"],
            "1563",
            "Museum Mayer van den Bergh",
            "MMB.0045",
            rights=PDM,
        ),
        eu("/2048128/BE_14", "De intrige", "nl", ["Ensor, James"], "1890", "KMSKA", "2073"),
        eu(
            "/9200579/FR_15",
            "Memories (Lawn Tennis)",
            "fr",
            ["Khnopff, Fernand"],
            "1889",
            "Fine Arts Belgium",
            "inv. 6162",
        ),
        eu(
            "/2048128/BE_18",
            "Portret van Marguerite van Mons",
            "nl",
            ["Rysselberghe, Théo van"],
            "1886",
            "MSK Gent",
            "1985-B",
            rights=CC0,
        ),
        eu(
            "/9200579/FR_20",
            "Le Roi boit",
            "fr",
            ["Jordaens, Jacob"],
            "ca. 1640",
            "Musées royaux des Beaux-Arts de Belgique",
            "3545",
        ),
        eu(
            "/2048128/BE_22",
            "Portret van Antoon van Bourgondië",
            "nl",
            ["Weyden, Rogier van der"],
            "ca. 1460",
            "KMSKB",
            "1453",
            rights=PDM,
        ),
        # a provider that is not in the institution reference table yet
        eu(
            "/2048128/BE_90",
            "Gezicht op de Leie",
            "nl",
            ["Claus, Emile"],
            "1891",
            "Museum van Deinze en de Leiestreek",
            "D.0213",
            rights=CC0,
            dctype="schilderij",
        ),
    ]


def web(ident, name, creator, date, medium, publisher, desc, lang="nl", license_=CC0):
    slug = ident.replace(".", "-").lower()
    p = {
        "method": "jsonld",
        "url": f"https://collectie.museabrugge.example/object/{slug}",
        "@type": "VisualArtwork",
        "identifier": ident,
        "name": name,
        "inLanguage": lang,
        "creator": {"@type": "Person", "name": creator},
        "dateCreated": date,
        "artMedium": medium,
        "image": {
            "@type": "ImageObject",
            "url": f"https://collectie.museabrugge.example/img/{slug}.jpg",
        },
        "publisher": {"@type": "Organization", "name": publisher},
        "description": desc,
        "license": license_,
    }
    return rec("musea_brugge", ident, p["url"], p)


def web_records():
    g, s = "Musea Brugge – Groeningemuseum", "Musea Brugge – Sint-Janshospitaal"
    return [
        web(
            "0000.GRO0161.I",
            "Madonna met kanunnik Joris van der Paele",
            "Jan van Eyck",
            "1436",
            "Olieverf op paneel",
            g,
            "Maria met Kind, geflankeerd door de heiligen Donatianus en Joris.",
        ),
        web(
            "0000.GRO0208.I",
            "Het Laatste Oordeel",
            "Jheronimus Bosch",
            "ca. 1495-1505",
            "Olieverf op paneel",
            g,
            "Drieluik met het paradijs, het Laatste Oordeel en de hel.",
        ),
        web(
            "0000.GRO0239.I",
            "Moreeltriptiek",
            "Hans Memlinc",
            "1484",
            "Olieverf op paneel",
            g,
            "Drieluik met de heilige Christoffel en de familie Moreel als schenkers.",
        ),
        web(
            "O.SJ0176.I",
            "Ursulaschrijn",
            "Hans Memling",
            "vóór 1489",
            "Olieverf op verguld eikenhout",
            s,
            "Reliekschrijn met taferelen uit de legende van de heilige Ursula.",
        ),
        web(
            "0000.GRO0040.I",
            "Het oordeel van Cambyses",
            "Gerard David",
            "1498",
            "Olieverf op paneel",
            g,
            "Tweeluik over de omkoopbare rechter Sisamnes en zijn bestraffing.",
        ),
        web(
            "0000.GRO1234.I",
            "Portret van een dame met rozenkrans",
            "Anoniem (Brugge)",
            "16de eeuw",
            "Olieverf op paneel",
            g,
            "Halffiguurportret van een vrouw met een koralen rozenkrans.",
        ),
    ]


INHOUSE = [
    (
        "IH-001",
        "Sint-Baafskathedraal",
        "",
        "Adoration of the Mystic Lamb",
        "Jan van Eyck",
        "altarpiece;Flemish Primitives;Eucharist",
        "Anchor work for the iconography strand.",
        "no",
    ),
    (
        "IH-002",
        "KMSKB",
        "inv 584",
        "Rebel Angels (Bruegel)",
        "P. Bruegel I",
        "demons;Last Judgement;moralising",
        "Compare demon typology with Bosch.",
        "yes",
    ),
    (
        "IH-003",
        "Groeninge",
        "0000.GRO0208.I",
        "Last Judgement triptych",
        "Bosch",
        "demons;Last Judgement;hell",
        "Copy or autograph? Follow the dendro report.",
        "yes",
    ),
    (
        "IH-004",
        "Onze-Lieve-Vrouwekerk Brugge",
        "",
        "Madonna of Bruges",
        "Michelangelo",
        "sculpture;Italian import;Virgin and Child",
        "Only Michelangelo to leave Italy in his lifetime.",
        "no",
    ),
    (
        "IH-005",
        "Fine Arts Belgium",
        "inv. 6715",
        "L'Empire des lumières",
        "René Magritte",
        "surrealism;night and day",
        "Several versions exist; this one is the Brussels canvas.",
        "no",
    ),
    (
        "IH-006",
        "MRBAB",
        "6768",
        "Des caresses",
        "Khnopff, Fernand",
        "symbolism;sphinx;androgyny",
        "",
        "no",
    ),
    (
        "IH-007",
        "KMSKA",
        "",
        "As the Old Sang, So the Young Pipe",
        "Jacob Jordaens",
        "proverb;family;music",
        "Proverb series; link to the Brussels version.",
        "yes",
    ),
    (
        "IH-008",
        "M Leuven",
        "",
        "Unidentified altarpiece wing (research lead)",
        "Unknown",
        "altarpiece;attribution open",
        "Seen in a 1920s auction catalogue; not yet in any database.",
        "no",
    ),
]


def main():
    raw = ROOT / "raw"
    groups = {
        "wikidata": wikidata_records(),
        "europeana": europeana_records(),
        "musea_brugge": web_records(),
    }
    for source, records in groups.items():
        d = raw / source
        d.mkdir(parents=True, exist_ok=True)
        with (d / "2026-10-01.jsonl").open("w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # a week later, one Wikidata item was edited: a new version lands in the raw zone
    changed = json.loads(json.dumps(groups["wikidata"][2]))
    changed["payload"]["itemDescription"] = (
        "painting, probably a copy after Pieter Bruegel the Elder"
    )
    changed["fetched_at"] = D2
    changed["content_hash"] = h(changed["payload"])
    with (raw / "wikidata" / "2026-10-08.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(changed, ensure_ascii=False) + "\n")

    with (ROOT / "inhouse_catalogue.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "catalogue_id",
                "institution",
                "inventory_no",
                "working_title",
                "artist",
                "themes",
                "research_notes",
                "image_rights_cleared",
            ]
        )
        w.writerows(INHOUSE)
    n = sum(len(v) for v in groups.values())
    print(f"wrote {n} raw records (+1 later version) and {len(INHOUSE)} in-house rows to {ROOT}")


if __name__ == "__main__":
    main()
