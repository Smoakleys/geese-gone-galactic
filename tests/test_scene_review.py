"""Vision-on-render scene review: the deterministic recognition core + the model wiring."""

from __future__ import annotations

from game.godot.scene_review import concepts_in, reads_as_pond_scene, review_render


# The two REAL descriptions the local vision model gave (recorded in docs/SCORECARD.md): the new modelled
# village vs the old blob art. The classifier must separate them.
_NEW_VILLAGE = "a serene rural scene with swans, nests, trees, houses, and a small water body surrounded by greenery"
_OLD_BLOB = "a green square with a blue square inside and a small orange shape"


def test_new_village_reads_as_a_pond_scene():
    ok, cats = reads_as_pond_scene(_NEW_VILLAGE)
    assert ok
    assert {"waterfowl", "water", "structure", "nature"} <= cats     # all four concepts recognised


def test_old_blob_does_not_read_as_a_pond_scene():
    ok, cats = reads_as_pond_scene(_OLD_BLOB)
    assert not ok and cats == set()                                  # only abstract shapes -> 0 concepts


def test_single_swan_reads_via_two_categories():
    # "This is a swan on the water" -> waterfowl + water = 2 -> passes; a lone concept does not.
    assert reads_as_pond_scene("This is a swan floating on the water.")[0]
    assert not reads_as_pond_scene("This is a swan.")[0]             # 1 category < min 2


def test_concepts_in_is_case_insensitive_and_specific():
    assert concepts_in("A GOOSE by a POND") == {"waterfowl", "water"}
    assert concepts_in("abstract coloured polygons") == set()


class _FakeVision:
    def __init__(self, desc): self.desc = desc

    def describe(self, image_path, question):
        return self.desc


def test_review_render_wires_description_to_classifier():
    ok, detail = review_render("x.png", _FakeVision(_NEW_VILLAGE))
    assert ok and "reads as a pond scene" in detail and "swans" in detail
    ok2, detail2 = review_render("x.png", _FakeVision(_OLD_BLOB))
    assert not ok2 and "does NOT read" in detail2


def test_review_render_never_raises_on_vision_failure():
    class _Boom:
        def describe(self, *a, **k):
            raise RuntimeError("model down")
    ok, detail = review_render("x.png", _Boom())
    assert not ok and "vision unavailable" in detail                 # advisory, not a crash
