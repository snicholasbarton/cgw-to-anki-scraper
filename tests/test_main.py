import argparse
from contextlib import nullcontext as does_not_raise

import pytest
from bs4 import BeautifulSoup

import main
from templates import INVALID_EXAMPLE_MODEL, TRANSLATION_MODEL, VALID_EXAMPLE_MODEL

TEST_CARD_BASE = {
    "model": TRANSLATION_MODEL,
    "hanzi": "你好",
    "pinyin": "nǐhǎo",
    "translation": "Hello",
    "notes": "A common greeting",
    "structure": "你好 + [Name]",
    "url": "https://resources.allsetlearning.com/chinese/grammar/ASDF1234",
    "article_title": "Ways to greet someone"
}


@pytest.fixture
def mock_soup_factory():
    def _create_soup(html_snippet):
        return BeautifulSoup(html_snippet, 'html.parser')
    return _create_soup


@pytest.mark.parametrize("url, expectation", [
    ("https://resources.allsetlearning.com/chinese/grammar/ASGH4A7W", does_not_raise()),
    ("https://resources.allsetlearning.com/chinese/grammar/A1_grammar_points", pytest.raises(argparse.ArgumentTypeError)),
    ("http://google.com", pytest.raises(argparse.ArgumentTypeError)), # Wrong domain
    ("not_a_url", pytest.raises(argparse.ArgumentTypeError))
])
def test_valid_cgw_url(url, expectation):
    with expectation:
        assert  main.is_valid_cgw_url(url) == url # the function just returns the argument


def test_extract_and_decompose_li_components(mock_soup_factory):
    html = """
    <li>
        我
        <span class="pinyin">wǒ</span>
        <span class="trans">I</span>
        <span class="expl">explanation</span>
    </li>
    """
    soup = mock_soup_factory(html)
    li = soup.find("li")

    h, p, t, e = main.extract_and_decompose_li_components(li)

    assert h == "我"
    assert p == "wǒ"
    assert t == "I"
    assert e == "explanation"

def test_extract_components_missing_optional_fields(mock_soup_factory):
    html = """<li>我<span class="trans">I</span></li>"""
    soup = mock_soup_factory(html)
    li = soup.find("li")

    h, p, t, e = main.extract_and_decompose_li_components(li)

    assert h == "我"
    assert p is None
    assert t == "I"
    assert e is None


def test_maybe_get_tag_text_and_decompose(mock_soup_factory):
    html = "<div><span class='target'>Got Me</span>Remaining</div>"
    soup = mock_soup_factory(html)
    tag = soup.find("span", class_="target")

    text = main.maybe_get_tag_text_and_decompose(tag)

    assert text == "Got Me"
    # ensure the tag was actually removed from the soup
    assert soup.find("span", class_="target") is None
    assert soup.get_text() == "Remaining"


@pytest.mark.parametrize("maybe_text, speaker_text, expected_result", [
    ("sample text", "A:", "A: sample text"),
    ("你好", "B:", "B: 你好"),
    (None, "A: ", None), # Should remain None if original text is None
])
def test_maybe_prepend_speaker_text(maybe_text, speaker_text, expected_result):
    assert main.maybe_prepend_speaker_text(maybe_text, speaker_text) == expected_result


def test_parse_level_pages(mock_soup_factory):
    html = """
    <html>
        <table class="wikitable">
            <tr><td><a href="/wiki/Wrong" title="Wrong">Link</a></td></tr>
            <tr><td><a href="/redirect" class="mw-redirect" title="Correct_Point">Target</a></td></tr>
        </table>
    </html>
    """
    # Create the TypedDict structure expected by the function
    page_data = [{"url": "http://level.url", "content": html}]

    urls = main.parse_level_pages(page_data)

    assert len(urls) == 1
    assert urls[0] == "https://resources.allsetlearning.com/chinese/grammar/Correct_Point"

def test_parse_point_page_standard_examples(mock_soup_factory):
    html = """
    <html>
        <h1>Grammar Point Title</h1>
        <div class="jiegou">Structure + Verb</div>
        <div class="liju">
            <ul>
                <li class="o">
                    <span class="pinyin">hǎo</span><span class="trans">Good</span>好
                </li>
                <li class="x">
                    <span class="pinyin">bù hǎo</span><span class="trans">Bad</span>不好
                </li>
            </ul>
        </div>
    </html>
    """
    page_data = {"url": "http://test.url", "content": html}
    cards = main.parse_point_page(page_data)

    assert len(cards) == 2

    # Check valid example
    assert cards[0]["model"] == VALID_EXAMPLE_MODEL
    assert cards[0]["hanzi"] == "好"
    assert cards[0]["structure"] == "Structure + Verb"

    # Check invalid example
    assert cards[1]["model"] == INVALID_EXAMPLE_MODEL
    assert cards[1]["hanzi"] == "不好"

def test_parse_point_page_dialog(mock_soup_factory):
    html = """
    <html>
        <h1>Dialog Title</h1>
        <div class="jiegou">Dialog Struct</div>
        <div class="liju">
            <ul class="dialog">
                <li>
                    <span class="speaker">A:</span>
                    <span class="pinyin">nǐ hǎo</span><span class="trans">Hello</span>你好
                </li>
                <li>
                    <span class="speaker">B:</span>
                    <span class="pinyin">hǎo</span><span class="trans">Hi</span>好
                </li>
            </ul>
        </div>
    </html>
    """
    page_data = {"url": "http://test.url", "content": html}
    cards = main.parse_point_page(page_data)

    assert len(cards) == 1  # Dialogs should be aggregated into one card
    card = cards[0]

    assert card["model"] == TRANSLATION_MODEL
    assert card["hanzi"] == "A: 你好<br>B: 好"
    assert card["translation"] == "A: Hello<br>B: Hi"
    assert card["structure"] == "Dialog Struct"


def test_parse_point_page_fallback_pinyin(mock_soup_factory):
    """Test that if pinyin span is missing, the script generates it using pypinyin."""
    html = """
    <html>
        <h1>Title</h1>
        <div class="liju">
            <ul>
                <li>你好<span class="trans">Hello</span></li>
            </ul>
        </div>
    </html>
    """
    page_data = {"url": "http://test.url", "content": html}
    cards = main.parse_point_page(page_data)

    assert len(cards) == 1
    assert "nǐ" in cards[0]["pinyin"]
    assert "hǎo" in cards[0]["pinyin"]


def test_diff_existing_and_scraped_all_new():
    existing = {}
    scraped = [TEST_CARD_BASE.copy()]

    to_export, stats = main.diff_existing_and_scraped(existing, scraped)

    assert len(to_export) == 1
    assert stats["new"] == 1
    assert stats["update"] == 0
    assert stats["skipped"] == 0


def test_diff_existing_and_scraped_identical_skip():
    # matches TEST_CARD_BASE
    existing = {
        "你好": {
            "pinyin": "nǐhǎo",
            "translation": "Hello"
        }
    }
    scraped = [TEST_CARD_BASE.copy()]

    to_export, stats = main.diff_existing_and_scraped(existing, scraped)

    assert len(to_export) == 0
    assert stats["new"] == 0
    assert stats["update"] == 0
    assert stats["skipped"] == 1


def test_diff_existing_and_scraped_update_translation():
    existing = {
        "你好": {
            "pinyin": "nǐhǎo",
            "translation": "Old Translation"
        }
    }
    scraped = [TEST_CARD_BASE.copy()]

    to_export, stats = main.diff_existing_and_scraped(existing, scraped)

    assert len(to_export) == 1
    assert stats["new"] == 0
    assert stats["update"] == 1
    assert stats["skipped"] == 0
    assert to_export[0]["translation"] == "Hello"


def test_diff_existing_and_scraped_ignores_whitespace():
    """Ensure trimming works so we don't update just for spaces."""
    existing = {
        "你好": {
            "pinyin": "nǐhǎo ", # trailing space
            "translation": "Hello"
        }
    }
    scraped_card = TEST_CARD_BASE.copy()
    scraped_card["pinyin"] = "nǐhǎo"
    scraped = [scraped_card]

    to_export, stats = main.diff_existing_and_scraped(existing, scraped)

    assert len(to_export) == 0
    assert stats["skipped"] == 1


def test_write_to_anki_deck(tmp_path):
    test_path = tmp_path / "test_deck.apkg"
    main.write_to_anki_deck([TEST_CARD_BASE], test_path)

    assert test_path.exists()


