# Chinese Grammar Wiki to Anki Scraper

[![CI](https://github.com/snicholasbarton/cgw-to-anki-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/snicholasbarton/cgw-to-anki-scraper/actions/workflows/ci.yml)

One of the most valuable tools I've found while trying to learn Chinese is [this shared Anki deck](https://ankiweb.net/shared/info/782551504) that has all the example sentences for each grammar point listed on the **[Chinese Grammar Wiki](https://resources.allsetlearning.com/chinese/grammar/Main_Page)**, organised into well-formatted flashcards. Sadly, that deck hasn't been updated since 2018 while the source content has been expanded and updated over time. The original logic that was used to generate this deck is also now outdated after some formatting changes to the Wiki.

This is my personal script designed to scrape all the example sentences and grammar explanations and put them in the same format as the original deck. It's also a good learning tool for me to brush up on the latest tools to write a Python scraping script!

---

## Setup & Installation

This project uses [uv](https://docs.astral.sh/uv/). You do not need to manage virtual environments manually; `uv` will handle it for you.

### 1. Install `uv`
If you don't have `uv` installed yet, do so before proceeding. Follow the instructions of your choice in the docs.

### 2. Clone the repo
```zsh
git clone [https://github.com/your-username/cgw-anki-scraper.git](https://github.com/snicholasbarton/cgw-anki-scraper.git)
cd cgw-anki-scraper
```
### 3. Install dependencies (optional)

If you want to install the deps before running the script, sync with `uv`. You can also do this to restore your venv if you mess it up somehow. Otherwise, `uv` will set up your venv for you the first time you run the script.
```zsh
uv sync
```

---

## Usage Instructions

There are four options available, plus the help message:

| Flag | Full Name | Description |
| :--- | :--- | :--- |
| `-h` | `--help` | Show the help message. |
| `-d` | `--deck` | **Update Existing Deck:** Path to an existing `.apkg` file. If provided, the script will add new examples to this deck. The learning progress and status of existing cards is preserved so long as your Anki import settings are set to always merge new cards. If omitted, a brand-new deck is created. |
| `-o` | `--output` | **Output Location:** Specify the filename for your new cards. Defaults to a deck in the `decks/` dir called `cgw_examples.apkg` if not specified. Try to keep outputs in the `decks/` dir. |
| `-t` | `--test` | **Test Mode:** A "dry-run" flag. It only scrapes **one** grammar point from **one** page. Highly recommended for first-time setup to verify everything is working without waiting for a full scrape. |
| n/a | `--test-url` | **Test URL:** Specify a single CGW grammar point URL, to be used in conjunction with the `-t` flag. Allows testing and debugging specific pages which might have structures not found across all pages, like dialog examples. |

### Running the Script

You should do a test run before running the whole script to ensure you have set up your environment correctly.

```zsh
# Run a quick test to ensure your environment is set up correctly
$ uv run main.py --test

# Scrape and save to a specific filename
$ uv run main.py --output decks/my_chinese_notes.apkg

# Update an existing deck
$ uv run main.py --deck decks/existing_deck.apkg
```

---

## Disclaimer & Ethics

### Changes to CGW format could break this script without warning
Given that I'm a user of this script, I'll likely fix it if things do break, but don't assume that will actually happen. If the script stops working and you really need it to work, file a PR or fork the repo!

### Be a Good Web Citizen
**Try not to DDoS the Chinese Grammar Wiki.** The way the script is designed, there shouldn't be any concerns, but please use it responsibly:
* **Rate Limiting:** There is some simple rate limiting already included in the script. This makes it take longer, but please don't reduce or remove it and hammer the CGW servers because you're impatient (Cloudflare will likely stop you anyways...).
* **Testing:** Use the `--test` flag when debugging your setup or modifying templates.

---

## License

* **Code:** This script is licensed under the [MIT License](https://opensource.org/licenses/MIT).
* **Content:** All content scraped from the Chinese Grammar Wiki is under a [Creative Commons License](https://creativecommons.org/licenses/by-nc-sa/3.0/).

---

## Acknowledgments and Library Author Shoutouts



* **[Chinese Grammar Wiki](https://resources.allsetlearning.com/chinese/grammar/Main_Page):** By far the best Chinese language learning resource I have found so far.
* **[Chris Dodge (dodgecm)](https://github.com/dodgecm):** The original author of the Chinese Grammar Wiki Anki deck. The card templates produced by my script are essentially identical to his, as his design is really great. You can see his code to generate the original deck on his [grammar-wiki-crawler](https://github.com/dodgecm/grammar-wiki-crawler) repo.
* **[Kerrick Staley (kerrickstaley)](https://github.com/kerrickstaley):** The `genanki` library is so much easier than interfacing with the official Anki one, and I'm a heavy user.

---