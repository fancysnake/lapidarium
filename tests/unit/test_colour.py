import pytest

from lapidarium.mills.colour import contrast_ratio, mix

WHITE = "#ffffff"
BLACK = "#000000"


def test_contrast_ratio_spans_one_to_twenty_one():
    assert contrast_ratio(BLACK, WHITE) == pytest.approx(21)
    assert contrast_ratio("#777777", "#777777") == pytest.approx(1)


def test_mix_lays_a_share_of_one_colour_over_another():
    assert mix(BLACK, WHITE, share=0.5) == "#808080"
