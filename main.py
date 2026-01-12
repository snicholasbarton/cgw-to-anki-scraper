import argparse
import asyncio
import os
import random
import sqlite3
import tempfile
import zipfile
from typing import TypedDict
from urllib.parse import urlparse

import genanki
import nodriver as uc
from bs4 import BeautifulSoup, Tag
from pypinyin import Style, pinyin

from templates import INVALID_EXAMPLE_MODEL, TRANSLATION_MODEL, VALID_EXAMPLE_MODEL

# Constants

# Stable, unique IDs for deck, generated with random.randrange(1 << 30, 1 << 31)
# Unique 10-digit integers so we don't overwrite other decks & can diff existing decks generated with this script
DECK_ID = 1111957820
DECK_NAME = "Chinese Grammar Wiki Examples"
DEFAULT_DECK_LOCATION="decks/cgw_examples.apkg"
BASE_URL = "https://resources.allsetlearning.com/chinese/grammar/"

LEVELS_URLS = [
        "https://resources.allsetlearning.com/chinese/grammar/A1_grammar_points",
        "https://resources.allsetlearning.com/chinese/grammar/A2_grammar_points",
        "https://resources.allsetlearning.com/chinese/grammar/B1_grammar_points",
        "https://resources.allsetlearning.com/chinese/grammar/B2_grammar_points",
        "https://resources.allsetlearning.com/chinese/grammar/C1_grammar_points"
        # add the below when it's populated:
        # "https://resources.allsetlearning.com/chinese/grammar/C2_grammar_points"
    ]
# some pages are malformed or unfinished; ignore them
BLOCKLIST = [
    "https://resources.allsetlearning.com/chinese/grammar/ASGH4A7W"
]

# Types and Type Aliases
Url = str
PageContent = str
class UrlAndPageContent(TypedDict):
    url: Url
    content: PageContent
class CardContent(TypedDict):
    model: str
    hanzi: str
    pinyin: str
    translation: str
    notes: str
    structure: str
    url: str
    article_title: str
class DeckDiffStats(TypedDict):
    new: int
    update: int
    skipped: int



def is_valid_cgw_url(url: Url):
    """Checks if a string is a valid CGW URL with a scheme and network location."""
    try:
        result = urlparse(url)
        # Check if both scheme (e.g., http) and netloc (e.g., google.com) exist
        # and that it's (roughly) a CGW grammar point page
        if (all([result.scheme, result.netloc])
            and BASE_URL in url and url.lower() not in [level.lower() for level in LEVELS_URLS]):
            return url
        raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid URL: '{url}'. Must be a valid grammar point page from Chinese Grammar Wiki.")


async def open_browser():
    return await uc.start()


def close_browser(browser):
    browser.stop()


async def human_scroll(page):
    """Scrolls down some fraction of the page to mimic a human."""
    try:
        total_height = await page.evaluate("document.body.scrollHeight")
        scroll_step = random.randint(int(total_height/5), int(total_height/1.5))
        await page.evaluate(f"window.scrollTo(0, {scroll_step})")
    except Exception:
        # sometimes we fail to get the total page height, just ignore since it's not important that we succeed
        pass


async def get_with_verification(browser, urls: list[Url], is_test=False) -> list[UrlAndPageContent]:
    url_and_pages: list[UrlAndPageContent] = []
    has_validated = False

    for url in urls:
        if is_test and url_and_pages: # breaks if there is a single result
            break
        if url in BLOCKLIST: # ignore blocklisted urls
            continue
        page = await browser.get(url)

        # Cloudflare often needs a moment to 'validate' the connection
        # Nodriver handles the wait automatically, but a small delay helps
        if not has_validated:
            await page.wait(6)
            has_validated = True

        url_and_pages.append({"url":url, "content":await page.get_content()})

        # Rate limit & occasionally scroll to keep Cloudflare from marking us as a bot
        if random.random() < 0.5:
            await human_scroll(page)
        await asyncio.sleep(random.uniform(1,4.5))

    return url_and_pages


def parse_level_pages(level_pages: list[UrlAndPageContent]) -> list[Url]:
    point_urls: list[Url] = []
    for page in level_pages:
        soup = BeautifulSoup(page["content"], 'html.parser')
        point_page_links = soup.select("table.wikitable a.mw-redirect")
        point_urls.extend([f"{BASE_URL}{link.get("title")}" for link in point_page_links])
    return point_urls


def parse_point_pages(url_and_point_pages) -> list[CardContent]:
    scraped_cards = []
    for url_and_point_page in url_and_point_pages:
        scraped_cards.extend(parse_point_page(url_and_point_page))
    return scraped_cards


def parse_point_page(url_and_point_page: dict[str, str]) -> list[CardContent]:
    soup = BeautifulSoup(url_and_point_page["content"], 'html.parser')

    url = url_and_point_page["url"]
    title = soup.find("h1").get_text(strip=True)
    example_divs = soup.find_all("div", class_="liju")

    parsed = []
    for div in example_divs:
        structure_div = div.find_previous("div", class_="jiegou")
        # some points don't have associated structures on the page
        structure = structure_div.get_text(strip=True) if structure_div is not None else ""

        # determine if it's a dialog or not
        ul = div.find("ul")
        is_dialog = "dialog" in ul.get("class", [])
        lis = ul.find_all("li")

        if is_dialog:
            # accumulate all the lines in the dialog
            lines_hanzi = []
            lines_pinyin = []
            lines_trans = []
            lines_expl = []

            for li in lis:
                # dialogs: group all lines into one entry
                speaker_tag = li.find("span", class_="speaker")
                if speaker_tag is None:
                    print(f"Malformed dialog example on page {url} does not have required speaker tag")
                    continue

                # we must prefix hanzi, pinyin, and translation with this text
                speaker_text = speaker_tag.get_text(strip=True)
                speaker_tag.decompose()
                if speaker_text is None:
                    print(f"Malformed dialog example on page {url} does not have required speaker labels")
                    continue

                hanzi_text, pinyin_text, trans_text, expl_text = extract_and_decompose_li_components(li)

                lines_hanzi.append(maybe_prepend_speaker_text(hanzi_text, speaker_text))
                lines_pinyin.append(maybe_prepend_speaker_text(pinyin_text, speaker_text))
                lines_trans.append(maybe_prepend_speaker_text(trans_text, speaker_text))
                lines_expl.append(maybe_prepend_speaker_text(expl_text, speaker_text))

            # join all the lines with newlines
            # remember Anki cards are rendered as HTML, use <br> not \n
            hanzi_text = "<br>".join(lines_hanzi).strip()
            pinyin_text = "<br>".join(filter(None, lines_pinyin))
            trans_text = "<br>".join(filter(None, lines_trans))
            expl_text = "<br>".join(filter(None, lines_expl))

            # dialogs are always translations
            model = TRANSLATION_MODEL

            # check that required field is present
            if hanzi_text is None:
                print(f"Malformed example on page {url} does not have all required fields: hanzi: {hanzi_text}, pinyin: {pinyin_text}, translation: {trans_text}")
                # skip and handle manually
                continue

            # validation checks:
            # if no pinyin is included, add some, warning if there are any that have multiple pinyins
            if pinyin_text is None:
                pinyin_text = ''.join([item[0] for item in pinyin(hanzi_text, style=Style.TONE)])

            parsed.append({"model":model,
                            "hanzi":hanzi_text or "", # should never be None
                            "pinyin":pinyin_text or "", # might be None for in-/valid example types
                            "translation":trans_text or "", # might be None for in-/valid example types
                            "notes":expl_text or "", # might be None if there is no explanation, which we just ignore
                            "structure":structure or "", # should never be None
                            "url":url,
                            "article_title":title})

        else:
            for li in lis:
                hanzi_text, pinyin_text, trans_text, expl_text = extract_and_decompose_li_components(li)

                # determine the model from the example type
                is_o_class = "o" in li.get('class', [])
                is_x_class = "x" in li.get('class', [])
                if is_o_class:
                    model = VALID_EXAMPLE_MODEL
                elif is_x_class:
                    model = INVALID_EXAMPLE_MODEL
                else:
                    model = TRANSLATION_MODEL

                # check that required field is present
                if hanzi_text is None:
                    print(f"Malformed example on page {url} does not have all required fields: hanzi: {hanzi_text}, pinyin: {pinyin_text}, translation: {trans_text}")
                    # skip and handle manually
                    continue

                # validation checks:
                # if no pinyin is included, add some, warning if there are any that have multiple pinyins
                if pinyin_text is None:
                    pinyin_text = ''.join([word[0] for word in pinyin(hanzi_text, style=Style.TONE)])

                parsed.append({"model":model,
                            "hanzi":hanzi_text or "", # should never be None
                            "pinyin":pinyin_text or "", # might be None for in-/valid example types
                            "translation":trans_text or "", # might be None for in-/valid example types
                            "notes":expl_text or "", # might be None if there is no explanation, which we just ignore
                            "structure":structure or "", # should never be None
                            "url":url,
                            "article_title":title})
    return parsed


def extract_and_decompose_li_components(li_tag: Tag) -> tuple[str, str | None, str | None, str | None]:
    pinyin_tag = li_tag.find("span", class_="pinyin")
    trans_tag = li_tag.find("span", class_="trans")
    expl_tag = li_tag.find("span", class_="expl")

    pinyin_text = maybe_get_tag_text_and_decompose(pinyin_tag)
    trans_text = maybe_get_tag_text_and_decompose(trans_tag)
    expl_text = maybe_get_tag_text_and_decompose(expl_tag)

    hanzi_text = li_tag.get_text(strip=True).replace(' ', '')

    return hanzi_text, pinyin_text, trans_text, expl_text


def maybe_get_tag_text_and_decompose(tag: Tag) -> str | None:
    if tag:
        text = tag.get_text()
        tag.decompose()
        return text
    return None


def maybe_prepend_speaker_text(maybe_text: str | None, speaker_text: str):
    return f"{speaker_text} {maybe_text}" if maybe_text is not None else maybe_text


def get_existing_cards_from_deck(path_to_deck: str) -> dict[str, dict[str, str]]:
    """
    Returns: { 'hanzi': { 'pinyin', 'translation'} }
    """
    if not path_to_deck or not os.path.exists(path_to_deck):
        print(f"Could not find existing deck: {path_to_deck}")
        return {}

    print(f"Reading existing deck: {path_to_deck}...")
    existing_data_snips = {}

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(path_to_deck, 'r') as z:
                z.extractall(temp_dir)

            db_path = os.path.join(temp_dir, 'collection.anki2')
            if not os.path.exists(db_path):
                db_path = os.path.join(temp_dir, 'collection.anki21')

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                # Fetch all notes (cards are linked to notes via the notes table)
                cursor.execute("SELECT flds FROM notes")
                rows = cursor.fetchall()
                print(f"Fetched {len(rows)} from existing deck.")

                for row in rows:
                    # Anki fields are separated by 0x1f
                    fields = row[0].split('\x1f')
                    if fields:
                        hanzi_key = fields[0].strip()
                        # Store relevant fields to check for changes - doesn't need to be all fields!
                        existing_data_snips[hanzi_key] = {
                            "pinyin": fields[1] if len(fields) > 1 else "",
                            "translation": fields[2] if len(fields) > 2 else "",
                        }
        except Exception as e:
            print(f"Warning: Could not read deck ({e}). Proceeding as if deck is empty.")

    return existing_data_snips


def diff_existing_and_scraped(existing_cards, scraped_cards: list[CardContent]) -> tuple[list[CardContent], DeckDiffStats]:
    cards_to_export: list[CardContent] = []
    stats: DeckDiffStats = {"new": 0, "update": 0, "skipped": 0}
    for card in scraped_cards:
        hanzi = card["hanzi"]

        if hanzi not in existing_cards:
            cards_to_export.append(card)
            stats["new"] += 1
        else:
            existing = existing_cards[hanzi]
            # strip whitespace to avoid false positives
            if (card["translation"].strip() != existing["translation"].strip() or
                    card["pinyin"].strip() != existing["pinyin"].strip()):
                cards_to_export.append(card)
                stats["update"] += 1
            else:
                stats["skipped"] += 1
    return cards_to_export, stats


def write_to_anki_deck(anki_cards: list[CardContent], output_filename=DEFAULT_DECK_LOCATION):
    deck = genanki.Deck(DECK_ID, DECK_NAME)
    for card in anki_cards:
        note = genanki.Note(
            model = card["model"],
            # sort field is set by the model
            fields = [
                card["hanzi"],
                card["pinyin"],
                card["translation"],
                card["notes"],
                card["structure"],
                card["url"],
                card["article_title"]
            ],
            # allows determinisitic updating of cards
            # a more thorough implementation here might generate these in a better way
            # e.g. consider if we could use h/p/t and say that if any 2/3 match, then this is the same card:
            # this would allow CGW authors to e.g. fix errors in hanzi without losing card learning progress
            # likely this means the pinyin would change, but the gist is the same
            guid = genanki.guid_for(card["hanzi"])
        )
        deck.add_note(note)
    genanki.Package(deck).write_to_file(output_filename)


# TODO: create a "cheatsheet" with the interesting BeautifulSoup methods that I used
async def main():
    # allow reading in an existing deck. If no arguments are passed, creates a new deck; can save updated decks separately from old decks if desired
    parser = argparse.ArgumentParser(description="Scrapes all examples from Chinese Grammar Wiki into a new or existing Anki deck")
    parser.add_argument('-d', '--deck', help="Path to existing .apkg deck to update with new examples. New deck is created if not specified.", default=None)
    parser.add_argument('-o', '--output', help=f"Output filename for new cards. Writes to \"{DEFAULT_DECK_LOCATION}\" if not specified.", default=DEFAULT_DECK_LOCATION)
    parser.add_argument('-t', '--test', action='store_true', help="If enabled, only reads 1 grammar point from 1 page. Use for testing that script works on setup and debugging")
    parser.add_argument('--test-url', type=is_valid_cgw_url, help="If this option is set alongside the --test flag, then we will run the script only for the given page. Must be a valid Chinese Grammar Wiki grammar point URL", default=None)
    args = parser.parse_args()

    if args.test_url and not args.test:
        # not literally true but enforce good user practice
        parser.error("--test-url requires the --test flag to be set.")

    try:
        # start the browser - do this just once per script invocation to reuse the session & verification cookie
        browser = await open_browser()

        # if a test url is passed, don't bother going through the level pages, just get it immediately
        if args.test and args.test_url:
            point_urls: list[Url] = [args.test_url]
        else:
            # scrape all the levels pages
            level_pages: list[UrlAndPageContent] = await get_with_verification(browser, LEVELS_URLS, args.test)

            # extact point page urls
            point_urls: list[Url] = parse_level_pages(level_pages)

        # scrape all the point pages
        point_contents_raw: list[UrlAndPageContent] = await get_with_verification(browser, point_urls, args.test)

        # parse the point pages
        cards_to_export: list[CardContent] = parse_point_pages(point_contents_raw)
        stats: DeckDiffStats = {"new": len(cards_to_export), "update": 0, "skipped": 0}

        path_to_deck = args.deck
        # if an existing deck is being updated, understand which cards are present
        if path_to_deck is not None and os.path.exists(path_to_deck):
            existing_cards = get_existing_cards_from_deck(args.deck)
            cards_to_export, stats = diff_existing_and_scraped(existing_cards, cards_to_export)

        if len(cards_to_export) == 0:
            print("Nothing to export!")
        else:
            # write out the anki deck
            write_to_anki_deck(cards_to_export, args.output)

            print(f"Success! Generated deck at '{args.output}'.")
        print("\n--- Report ---")
        print(f"New Cards: {stats["new"]}")
        print(f"Updates:   {stats["update"]} (Content changed)")
        print(f"Skipped:   {stats["skipped"]} (Identical)")

    finally:
        # Always close the browser at the end of the session
        close_browser(browser)

if __name__ == "__main__":
    asyncio.run(main())
