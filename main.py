import json
import random
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Hungarian Bible API (EFO)",
    description="REST API for the Hungarian Bible — Egyszerű fordítás (EFO). 66 books, ~31,000 verses.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BIBLE_DATA: dict = {}
BOOKS_BY_CODE: dict = {}
CHAPTERS_INDEX: dict = {}
VERSES_INDEX: dict = {}
ALL_VERSES: list = []

ENGLISH_TO_CODE: dict = {}


def _build_english_map():
    """Map common English book names/abbreviations to standard codes."""
    mapping = {
        "genesis": "GEN", "gen": "GEN",
        "exodus": "EXO", "exo": "EXO", "exod": "EXO",
        "leviticus": "LEV", "lev": "LEV",
        "numbers": "NUM", "num": "NUM",
        "deuteronomy": "DEU", "deu": "DEU", "deut": "DEU",
        "joshua": "JOS", "jos": "JOS", "josh": "JOS",
        "judges": "JDG", "jdg": "JDG", "judg": "JDG",
        "ruth": "RUT", "rut": "RUT",
        "1 samuel": "1SA", "1samuel": "1SA", "1sam": "1SA", "1 sam": "1SA",
        "2 samuel": "2SA", "2samuel": "2SA", "2sam": "2SA", "2 sam": "2SA",
        "1 kings": "1KI", "1kings": "1KI", "1kgs": "1KI", "1 kgs": "1KI",
        "2 kings": "2KI", "2kings": "2KI", "2kgs": "2KI", "2 kgs": "2KI",
        "1 chronicles": "1CH", "1chronicles": "1CH", "1chr": "1CH", "1 chr": "1CH", "1 chron": "1CH",
        "2 chronicles": "2CH", "2chronicles": "2CH", "2chr": "2CH", "2 chr": "2CH", "2 chron": "2CH",
        "ezra": "EZR", "ezr": "EZR",
        "nehemiah": "NEH", "neh": "NEH",
        "esther": "EST", "est": "EST", "esth": "EST",
        "job": "JOB",
        "psalms": "PSA", "psalm": "PSA", "psa": "PSA", "ps": "PSA",
        "proverbs": "PRO", "pro": "PRO", "prov": "PRO",
        "ecclesiastes": "ECC", "ecc": "ECC", "eccl": "ECC",
        "song of solomon": "SNG", "song of songs": "SNG", "sng": "SNG", "sos": "SNG", "songs": "SNG",
        "isaiah": "ISA", "isa": "ISA",
        "jeremiah": "JER", "jer": "JER",
        "lamentations": "LAM", "lam": "LAM",
        "ezekiel": "EZK", "ezk": "EZK", "ezek": "EZK",
        "daniel": "DAN", "dan": "DAN",
        "hosea": "HOS", "hos": "HOS",
        "joel": "JOL", "jol": "JOL",
        "amos": "AMO", "amo": "AMO",
        "obadiah": "OBA", "oba": "OBA", "obad": "OBA",
        "jonah": "JON", "jon": "JON",
        "micah": "MIC", "mic": "MIC",
        "nahum": "NAH", "nah": "NAH",
        "habakkuk": "HAB", "hab": "HAB",
        "zephaniah": "ZEP", "zep": "ZEP", "zeph": "ZEP",
        "haggai": "HAG", "hag": "HAG",
        "zechariah": "ZEC", "zec": "ZEC", "zech": "ZEC",
        "malachi": "MAL", "mal": "MAL",
        "matthew": "MAT", "mat": "MAT", "matt": "MAT",
        "mark": "MRK", "mrk": "MRK",
        "luke": "LUK", "luk": "LUK",
        "john": "JHN", "jhn": "JHN", "jn": "JHN",
        "acts": "ACT", "act": "ACT",
        "romans": "ROM", "rom": "ROM",
        "1 corinthians": "1CO", "1corinthians": "1CO", "1cor": "1CO", "1 cor": "1CO",
        "2 corinthians": "2CO", "2corinthians": "2CO", "2cor": "2CO", "2 cor": "2CO",
        "galatians": "GAL", "gal": "GAL",
        "ephesians": "EPH", "eph": "EPH",
        "philippians": "PHP", "php": "PHP", "phil": "PHP",
        "colossians": "COL", "col": "COL",
        "1 thessalonians": "1TH", "1thessalonians": "1TH", "1thess": "1TH", "1 thess": "1TH",
        "2 thessalonians": "2TH", "2thessalonians": "2TH", "2thess": "2TH", "2 thess": "2TH",
        "1 timothy": "1TI", "1timothy": "1TI", "1tim": "1TI", "1 tim": "1TI",
        "2 timothy": "2TI", "2timothy": "2TI", "2tim": "2TI", "2 tim": "2TI",
        "titus": "TIT", "tit": "TIT",
        "philemon": "PHM", "phm": "PHM", "phlm": "PHM",
        "hebrews": "HEB", "heb": "HEB",
        "james": "JAS", "jas": "JAS",
        "1 peter": "1PE", "1peter": "1PE", "1pet": "1PE", "1 pet": "1PE",
        "2 peter": "2PE", "2peter": "2PE", "2pet": "2PE", "2 pet": "2PE",
        "1 john": "1JN", "1john": "1JN", "1jn": "1JN",
        "2 john": "2JN", "2john": "2JN", "2jn": "2JN",
        "3 john": "3JN", "3john": "3JN", "3jn": "3JN",
        "jude": "JUD", "jud": "JUD",
        "revelation": "REV", "rev": "REV", "revelations": "REV",
    }
    return mapping


@app.on_event("startup")
def load_bible_data():
    global BIBLE_DATA, BOOKS_BY_CODE, CHAPTERS_INDEX, VERSES_INDEX, ALL_VERSES, ENGLISH_TO_CODE

    data_path = Path(__file__).parent / "hungarian_bible.json"
    with open(data_path, "r", encoding="utf-8") as f:
        BIBLE_DATA = json.load(f)

    for book in BIBLE_DATA["books"]:
        code = book["book_code"].upper()
        BOOKS_BY_CODE[code] = book
        for chapter in book["chapters"]:
            ch_num = chapter["chapter"]
            CHAPTERS_INDEX[(code, ch_num)] = chapter
            for verse in chapter["verses"]:
                v_num = verse["verse"]
                VERSES_INDEX[(code, ch_num, v_num)] = verse
                ALL_VERSES.append({
                    "book_code": code,
                    "book_name": book["book_name"],
                    "chapter": ch_num,
                    "verse": v_num,
                    "text": verse["text"],
                })

    ENGLISH_TO_CODE = _build_english_map()


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.get("/", summary="API info", tags=["Info"])
def root():
    return {
        "name": "Hungarian Bible API (EFO)",
        "version": "1.0.0",
        "translation": BIBLE_DATA.get("translation", "Egyszerű fordítás (EFO)"),
        "language": BIBLE_DATA.get("language", "hu"),
        "total_books": len(BIBLE_DATA.get("books", [])),
        "total_verses": len(ALL_VERSES),
        "docs": "/docs",
    }


@app.get("/books", summary="List all books", tags=["Books"])
def list_books():
    return [
        {"book_code": book["book_code"], "book_name": book["book_name"]}
        for book in BIBLE_DATA["books"]
    ]


@app.get("/books/{book_code}", summary="Get a full book", tags=["Books"])
def get_book(book_code: str):
    book = BOOKS_BY_CODE.get(book_code.upper())
    if not book:
        raise HTTPException(status_code=404, detail=f"Book '{book_code}' not found")
    return book


@app.get("/books/{book_code}/chapters", summary="List chapters in a book", tags=["Chapters"])
def list_chapters(book_code: str):
    book = BOOKS_BY_CODE.get(book_code.upper())
    if not book:
        raise HTTPException(status_code=404, detail=f"Book '{book_code}' not found")
    return [
        {"chapter": ch["chapter"], "verse_count": len(ch["verses"])}
        for ch in book["chapters"]
    ]


@app.get("/books/{book_code}/chapters/{chapter}", summary="Get all verses in a chapter", tags=["Chapters"])
def get_chapter(book_code: str, chapter: int):
    ch = CHAPTERS_INDEX.get((book_code.upper(), chapter))
    if not ch:
        if book_code.upper() not in BOOKS_BY_CODE:
            raise HTTPException(status_code=404, detail=f"Book '{book_code}' not found")
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found in '{book_code}'")
    return {
        "book_code": book_code.upper(),
        "book_name": BOOKS_BY_CODE[book_code.upper()]["book_name"],
        "chapter": chapter,
        "verses": ch["verses"],
    }


@app.get("/books/{book_code}/chapters/{chapter}/verses/{verse}", summary="Get a single verse", tags=["Verses"])
def get_verse(book_code: str, chapter: int, verse: int):
    v = VERSES_INDEX.get((book_code.upper(), chapter, verse))
    if not v:
        if book_code.upper() not in BOOKS_BY_CODE:
            raise HTTPException(status_code=404, detail=f"Book '{book_code}' not found")
        if (book_code.upper(), chapter) not in CHAPTERS_INDEX:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found in '{book_code}'")
        raise HTTPException(status_code=404, detail=f"Verse {verse} not found in {book_code} chapter {chapter}")
    return {
        "book_code": book_code.upper(),
        "book_name": BOOKS_BY_CODE[book_code.upper()]["book_name"],
        "chapter": chapter,
        "verse": verse,
        "text": v["text"],
    }


@app.get("/verses", summary="Get a verse range", tags=["Verses"])
def get_verse_range(
    book: str = Query(..., description="Book code (e.g., GEN, JHN) or English name (e.g., Genesis, John)"),
    chapter: int = Query(..., description="Chapter number"),
    start_verse: int = Query(..., description="Start verse number"),
    end_verse: Optional[int] = Query(None, description="End verse number (inclusive). Omit for single verse."),
):
    code = book.upper()
    if code not in BOOKS_BY_CODE:
        code = ENGLISH_TO_CODE.get(book.lower(), "")
    if not code or code not in BOOKS_BY_CODE:
        raise HTTPException(status_code=404, detail=f"Book '{book}' not found")

    if end_verse is None:
        end_verse = start_verse

    verses = []
    for v_num in range(start_verse, end_verse + 1):
        v = VERSES_INDEX.get((code, chapter, v_num))
        if v:
            verses.append({"verse": v_num, "text": v["text"]})

    if not verses:
        raise HTTPException(status_code=404, detail=f"No verses found for {code} {chapter}:{start_verse}-{end_verse}")

    return {
        "book_code": code,
        "book_name": BOOKS_BY_CODE[code]["book_name"],
        "chapter": chapter,
        "verses": verses,
        "combined_text": " ".join(v["text"] for v in verses),
    }


class LookupReference(BaseModel):
    book: str
    chapter: int
    start_verse: int
    end_verse: Optional[int] = None


class LookupRequest(BaseModel):
    references: list[LookupReference]


@app.post("/lookup", summary="Batch lookup multiple verse references", tags=["Lookup"])
def batch_lookup(request: LookupRequest):
    results = []
    for ref in request.references:
        code = ref.book.upper()
        if code not in BOOKS_BY_CODE:
            code = ENGLISH_TO_CODE.get(ref.book.lower(), "")

        if not code or code not in BOOKS_BY_CODE:
            results.append({
                "reference": f"{ref.book} {ref.chapter}:{ref.start_verse}",
                "error": f"Book '{ref.book}' not found",
                "verses": [],
            })
            continue

        end_v = ref.end_verse if ref.end_verse else ref.start_verse
        verses = []
        for v_num in range(ref.start_verse, end_v + 1):
            v = VERSES_INDEX.get((code, ref.chapter, v_num))
            if v:
                verses.append({"verse": v_num, "text": v["text"]})

        book_name = BOOKS_BY_CODE[code]["book_name"]
        ref_str = f"{book_name} {ref.chapter}:{ref.start_verse}"
        if ref.end_verse and ref.end_verse != ref.start_verse:
            ref_str += f"-{ref.end_verse}"

        results.append({
            "reference": ref_str,
            "book_code": code,
            "book_name": book_name,
            "chapter": ref.chapter,
            "verses": verses,
            "combined_text": " ".join(v["text"] for v in verses),
        })

    return {"results": results}


@app.get("/search", summary="Search verses by text", tags=["Search"])
def search_verses(
    q: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results to skip"),
):
    q_lower = q.lower()
    matches = [v for v in ALL_VERSES if q_lower in v["text"].lower()]
    total = len(matches)
    page = matches[offset: offset + limit]
    return {
        "query": q,
        "total_results": total,
        "limit": limit,
        "offset": offset,
        "results": page,
    }


@app.get("/random", summary="Get a random verse", tags=["Random"])
def random_verse():
    return random.choice(ALL_VERSES)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
