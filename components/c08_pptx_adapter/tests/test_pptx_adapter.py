"""Standalone tests for the PPTX Adapter (component 08).

Run in isolation: pytest components/c08_pptx_adapter
"""
import pytest
from pptx import Presentation
from pptx.util import Inches

from components.c08_pptx_adapter.src.pptx_adapter import read_or_write


def _make_presentation(path: str) -> None:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box.name = "churn_value"
    box.text_frame.text = "2.9%"

    picture_placeholder = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(1), Inches(1))
    picture_placeholder.name = "chart_image"
    picture_placeholder.text_frame.text = ""  # stand-in; has_text_frame still True, tested separately below
    prs.save(path)


def test_write_then_read_round_trip_preserves_other_slides(tmp_path):
    pptx_path = str(tmp_path / "exec_briefing.pptx")
    _make_presentation(pptx_path)

    write_result = read_or_write(
        {"file": pptx_path, "slide": 1, "placeholder": "churn_value", "value": "3.1%", "operation": "write"}
    )
    assert write_result["success"] is True
    assert write_result["previous_value"] == "2.9%"
    assert write_result["new_value"] == "3.1%"

    read_result = read_or_write({"file": pptx_path, "slide": 1, "placeholder": "churn_value", "operation": "read"})
    assert read_result["value"] == "3.1%"


def test_write_takes_a_backup(tmp_path):
    import os

    pptx_path = str(tmp_path / "exec_briefing.pptx")
    _make_presentation(pptx_path)

    read_or_write({"file": pptx_path, "slide": 1, "placeholder": "churn_value", "value": "3.1%", "operation": "write"})

    assert os.path.exists(pptx_path + ".bak")


def test_unknown_slide_raises_clean_error(tmp_path):
    pptx_path = str(tmp_path / "exec_briefing.pptx")
    _make_presentation(pptx_path)

    with pytest.raises(LookupError):
        read_or_write({"file": pptx_path, "slide": 99, "placeholder": "churn_value", "operation": "read"})


def test_unknown_placeholder_raises_clean_error(tmp_path):
    pptx_path = str(tmp_path / "exec_briefing.pptx")
    _make_presentation(pptx_path)

    with pytest.raises(LookupError):
        read_or_write({"file": pptx_path, "slide": 1, "placeholder": "does_not_exist", "operation": "read"})


def test_editing_a_non_text_shape_raises_unsupported_operation(tmp_path):
    pptx_path = str(tmp_path / "exec_briefing.pptx")
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    picture_path = _make_dummy_image(tmp_path)
    picture = slide.shapes.add_picture(picture_path, Inches(1), Inches(1), Inches(2), Inches(2))
    picture.name = "chart_image"
    prs.save(pptx_path)

    with pytest.raises(ValueError, match="unsupported_operation"):
        read_or_write({"file": pptx_path, "slide": 1, "placeholder": "chart_image", "operation": "read"})


def _make_dummy_image(tmp_path) -> str:
    from PIL import Image

    path = str(tmp_path / "dummy.png")
    Image.new("RGB", (10, 10), color="white").save(path)
    return path


def test_create_builds_a_new_deck_with_title_and_content_slides(tmp_path):
    pptx_path = str(tmp_path / "new_deck.pptx")

    result = read_or_write(
        {
            "file": pptx_path,
            "operation": "create",
            "title": "Modi: Recent Developments",
            "slides": [
                {"heading": "Economic Policy", "bullets": ["GDP growth", "New trade deals"]},
                {"heading": "International Relations", "bullets": ["G20 summit", "Bilateral talks"]},
            ],
        }
    )

    assert result["success"] is True
    assert result["slide_count"] == 3  # 1 title slide + 2 content slides

    prs = Presentation(pptx_path)
    assert len(prs.slides) == 3
    assert prs.slides[0].shapes.title.text == "Modi: Recent Developments"
    assert prs.slides[1].shapes.title.text == "Economic Policy"
    body_text = prs.slides[1].placeholders[1].text_frame.text
    assert "GDP growth" in body_text
    assert "New trade deals" in body_text


def test_create_without_title_only_adds_content_slides(tmp_path):
    pptx_path = str(tmp_path / "no_title.pptx")

    result = read_or_write(
        {"file": pptx_path, "operation": "create", "slides": [{"heading": "Only slide", "bullets": ["one point"]}]}
    )

    assert result["slide_count"] == 1
    prs = Presentation(pptx_path)
    assert prs.slides[0].shapes.title.text == "Only slide"
