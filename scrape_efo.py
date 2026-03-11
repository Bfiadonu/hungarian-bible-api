"""
Scrape the EFO (Egyszerű fordítás) Hungarian Bible from holybible.site.
Outputs hungarian_bible.json in the same format as bengali_bible.json.
"""
import json
import re
import time
import urllib.request
from html.parser import HTMLParser

BASE_URL = "https://holybible.site/chapter.php?version=efo&book={book}&chapter={chapter}"

BOOKS = [
    # (url_name, standard_code, hungarian_name, chapter_count)
    # Old Testament
    ("genesis", "GEN", "1 Mózes", 50),
    ("exodus", "EXO", "2 Mózes", 40),
    ("leviticus", "LEV", "3 Mózes", 27),
    ("numbers", "NUM", "4 Mózes", 36),
    ("deuteronomy", "DEU", "5 Mózes", 34),
    ("joshua", "JOS", "Józsué", 24),
    ("judges", "JDG", "Bírák", 21),
    ("ruth", "RUT", "Ruth", 4),
    ("1-samuel", "1SA", "1 Sámuel", 31),
    ("2-samuel", "2SA", "2 Sámuel", 24),
    ("1-kings", "1KI", "1 Királyok", 22),
    ("2-kings", "2KI", "2 Királyok", 25),
    ("1-chronicles", "1CH", "1 Krónikák", 29),
    ("2-chronicles", "2CH", "2 Krónikák", 36),
    ("ezra", "EZR", "Ezsdrás", 10),
    ("nehemiah", "NEH", "Nehémiás", 13),
    ("esther", "EST", "Eszter", 10),
    ("job", "JOB", "Jób", 42),
    ("psalms", "PSA", "Zsoltárok", 150),
    ("proverbs", "PRO", "Példabeszédek", 31),
    ("ecclesiastes", "ECC", "Prédikátor", 12),
    ("song-of-solomon", "SNG", "Énekek Éneke", 8),
    ("isaiah", "ISA", "Ézsaiás", 66),
    ("jeremiah", "JER", "Jeremiás", 52),
    ("lamentations", "LAM", "Siralmak", 5),
    ("ezekiel", "EZK", "Ezékiel", 48),
    ("daniel", "DAN", "Dániel", 12),
    ("hosea", "HOS", "Hóseás", 14),
    ("joel", "JOL", "Jóel", 3),
    ("amos", "AMO", "Ámósz", 9),
    ("obadiah", "OBA", "Abdiás", 1),
    ("jonah", "JON", "Jónás", 4),
    ("micah", "MIC", "Mikeás", 7),
    ("nahum", "NAH", "Náhum", 3),
    ("habakkuk", "HAB", "Habakuk", 3),
    ("zephaniah", "ZEP", "Sofóniás", 3),
    ("haggai", "HAG", "Haggeus", 2),
    ("zechariah", "ZEC", "Zakariás", 14),
    ("malachi", "MAL", "Malakiás", 4),
    # New Testament
    ("matthew", "MAT", "Máté", 28),
    ("mark", "MRK", "Márk", 16),
    ("luke", "LUK", "Lukács", 24),
    ("john", "JHN", "János", 21),
    ("acts", "ACT", "Apostolok", 28),
    ("romans", "ROM", "Róma", 16),
    ("1-corinthians", "1CO", "1 Korinthus", 16),
    ("2-corinthians", "2CO", "2 Korinthus", 13),
    ("galatians", "GAL", "Galata", 6),
    ("ephesians", "EPH", "Efézus", 6),
    ("philippians", "PHP", "Filippi", 4),
    ("colossians", "COL", "Kolossé", 4),
    ("1-thessalonians", "1TH", "1 Thesszalonika", 5),
    ("2-thessalonians", "2TH", "2 Thesszalonika", 3),
    ("1-timothy", "1TI", "1 Timóteus", 6),
    ("2-timothy", "2TI", "2 Timóteus", 4),
    ("titus", "TIT", "Titusz", 3),
    ("philemon", "PHM", "Filemon", 1),
    ("hebrews", "HEB", "Zsidók", 13),
    ("james", "JAS", "Jakab", 5),
    ("1-peter", "1PE", "1 Péter", 5),
    ("2-peter", "2PE", "2 Péter", 3),
    ("1-john", "1JN", "1 János", 5),
    ("2-john", "2JN", "2 János", 1),
    ("3-john", "3JN", "3 János", 1),
    ("jude", "JUD", "Júdás", 1),
    ("revelation", "REV", "Jelenések", 22),
]


class VerseParser(HTMLParser):
    """Parse verses from holybible.site chapter pages."""
    def __init__(self):
        super().__init__()
        self.verses = []
        self.in_verse_link = False
        self.current_verse_num = None
        self.capture_text = False
        self.current_text = []
        self.in_content = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Verse links look like: <a href="verse.php?version=efo&book=...&verse=N">N</a>
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if "verse.php?" in href and "version=efo" in href:
                # Extract verse number from href
                m = re.search(r'verse=(\d+)', href)
                if m:
                    # Save previous verse if any
                    if self.current_verse_num is not None and self.current_text:
                        text = " ".join(self.current_text).strip()
                        text = re.sub(r'\s+', ' ', text)
                        if text:
                            self.verses.append({
                                "verse": self.current_verse_num,
                                "text": text
                            })
                    self.current_verse_num = int(m.group(1))
                    self.current_text = []
                    self.in_verse_link = True

    def handle_endtag(self, tag):
        if tag == "a" and self.in_verse_link:
            self.in_verse_link = False
            self.capture_text = True

    def handle_data(self, data):
        if self.in_verse_link:
            return  # Skip the verse number text inside the link
        if self.capture_text and self.current_verse_num is not None:
            text = data.strip()
            if text and text != ".":
                # Remove leading ". " from verse text
                text = re.sub(r'^\.\s*', '', text)
                if text:
                    self.current_text.append(text)

    def finalize(self):
        """Call after feeding all data to capture the last verse."""
        if self.current_verse_num is not None and self.current_text:
            text = " ".join(self.current_text).strip()
            text = re.sub(r'\s+', ' ', text)
            if text:
                self.verses.append({
                    "verse": self.current_verse_num,
                    "text": text
                })


def fetch_chapter(book_url, chapter):
    url = BASE_URL.format(book=book_url, chapter=chapter)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")

    parser = VerseParser()
    parser.feed(html)
    parser.finalize()
    return parser.verses


def main():
    bible_data = {
        "translation": "Egyszerű fordítás (EFO)",
        "language": "hu",
        "books": [],
        "stats": {
            "total_books": 66,
            "total_verses": 0
        }
    }

    total_verses = 0

    for book_url, code, hun_name, chapters in BOOKS:
        print(f"Scraping {code} ({hun_name}) - {chapters} chapters...")
        book = {
            "book_code": code,
            "book_name": hun_name,
            "chapters": []
        }

        for ch in range(1, chapters + 1):
            try:
                verses = fetch_chapter(book_url, ch)
                book["chapters"].append({
                    "chapter": ch,
                    "verses": verses
                })
                total_verses += len(verses)
                if ch % 10 == 0:
                    print(f"  Chapter {ch}/{chapters} ({len(verses)} verses)")
                time.sleep(0.3)  # Be polite
            except Exception as e:
                print(f"  ERROR: {code} ch {ch}: {e}")
                book["chapters"].append({
                    "chapter": ch,
                    "verses": []
                })
                time.sleep(2)

        bible_data["books"].append(book)
        print(f"  Done: {sum(len(c['verses']) for c in book['chapters'])} verses")

    bible_data["stats"]["total_verses"] = total_verses

    out_path = "hungarian_bible.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bible_data, f, ensure_ascii=False)

    print(f"\nComplete! {total_verses} verses saved to {out_path}")


if __name__ == "__main__":
    main()
