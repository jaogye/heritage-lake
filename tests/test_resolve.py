from lake.normalize import SilverRecord, norm_inventory
from lake.resolve import MATCH, resolve, score_pair


def rec(key, **kw):
    source, sid = key.split(":", 1)
    base = dict(
        record_key=key,
        source=source,
        source_id=sid,
        url=None,
        title=None,
        institution="Royal Museums of Fine Arts of Belgium",
        institution_known=True,
    )
    return SilverRecord(**(base | kw))


BRUEGEL = dict(creator_keys=["bruegel"])


def test_inventory_number_variants_normalise():
    assert (
        norm_inventory("inv. 0584")
        == norm_inventory("Inv.nr. 584")
        == norm_inventory("584")
        == "584"
    )
    assert norm_inventory("0000.GRO0208.I") == "0000.gro0208.i"


def test_same_inventory_merges_despite_different_language_titles():
    a = rec(
        "wikidata:Q1",
        title="The Fall of the Rebel Angels",
        inventory_no="584",
        year_start=1562,
        year_end=1562,
        wikidata_qid="Q1",
        **BRUEGEL,
    )
    b = rec(
        "europeana:/x/1",
        title="De val van de opstandige engelen",
        inventory_no="584",
        year_start=1562,
        year_end=1562,
        **BRUEGEL,
    )
    score, why = score_pair(a, b)
    assert score >= MATCH
    assert any("inventory" in w for w in why)


def test_same_painter_same_museum_different_inventory_is_not_a_match():
    icarus = rec(
        "wikidata:Q3",
        title="Landscape with the Fall of Icarus",
        inventory_no="4030",
        year_start=1555,
        year_end=1565,
        **BRUEGEL,
    )
    angels = rec(
        "europeana:/x/1",
        title="De val van de opstandige engelen",
        inventory_no="584",
        year_start=1562,
        year_end=1562,
        **BRUEGEL,
    )
    score, _ = score_pair(icarus, angels)
    assert score < 5


def test_without_inventory_goes_to_review_not_merge():
    a = rec(
        "wikidata:Q4", title="The Census at Bethlehem", year_start=1566, year_end=1566, **BRUEGEL
    )
    b = rec(
        "europeana:/x/4",
        title="De volkstelling te Bethlehem",
        year_start=1566,
        year_end=1566,
        **BRUEGEL,
    )
    entity_of, links = resolve([a, b])
    assert entity_of[a.record_key] != entity_of[b.record_key]
    assert links[0].decision == "review"


def test_curator_decision_settles_review():
    a = rec(
        "wikidata:Q4", title="The Census at Bethlehem", year_start=1566, year_end=1566, **BRUEGEL
    )
    b = rec(
        "europeana:/x/4",
        title="De volkstelling te Bethlehem",
        year_start=1566,
        year_end=1566,
        **BRUEGEL,
    )
    entity_of, links = resolve([a, b], {frozenset((a.record_key, b.record_key)): "accept"})
    assert entity_of[a.record_key] == entity_of[b.record_key]
    assert "curator accepted" in links[0].reasons


def test_transitive_merge_cannot_join_two_qids():
    # x looks like both q1 and q2 (same inventory as each, e.g. a data-entry error upstream)
    q1 = rec("wikidata:Q1", inventory_no="10", wikidata_qid="Q1", **BRUEGEL)
    q2 = rec("wikidata:Q2", inventory_no="10", wikidata_qid="Q2", **BRUEGEL)
    x = rec("europeana:/x/9", inventory_no="10", **BRUEGEL)
    entity_of, links = resolve([q1, q2, x])
    assert entity_of[q1.record_key] != entity_of[q2.record_key]
    assert any(lk.decision == "blocked" for lk in links)


def test_entity_ids_are_stable_and_anchored_on_wikidata():
    a = rec("wikidata:Q1", inventory_no="1", wikidata_qid="Q1", **BRUEGEL)
    b = rec("europeana:/x/1", inventory_no="1", **BRUEGEL)
    e1, _ = resolve([a, b])
    e2, _ = resolve([b, a])
    assert e1 == e2
