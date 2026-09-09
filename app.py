import csv
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "management_radar.db"
LINKS_CSV = BASE_DIR / "disclosure_links.csv"

app = Flask(__name__)

TOPIC_KEYWORDS = {
    "expansion": ["expansion", "capacity", "plant", "facility", "new factory", "manufacturing", "scale"],
    "margin": ["margin", "ebitda", "profitability", "cost", "pricing", "operating margin"],
    "management_change": ["resign", "ceo", "cfo", "succession", "appointment", "change in leadership"],
    "growth": ["growth", "sales", "demand", "orders", "revenue", "pipeline", "deal"],
    "risk": ["risk", "slowdown", "inflation", "supply", "challenging", "uncertainty"],
    "ai": ["ai", "artificial intelligence", "automation", "digital", "cloud", "genai"],
    "deal_flow": ["deal", "contract", "wins", "orders", "pipeline", "client"],
}


def ensure_directories() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    ensure_directories()
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sector TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                cached_path TEXT,
                content TEXT,
                date TEXT,
                FOREIGN KEY(company_id) REFERENCES companies(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS text_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                citation TEXT NOT NULL,
                content TEXT NOT NULL,
                snippet TEXT,
                tags TEXT,
                FOREIGN KEY(company_id) REFERENCES companies(id),
                FOREIGN KEY(source_id) REFERENCES sources(id)
            )
            """
        )


def get_company_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    conn.execute("INSERT INTO companies (name, sector) VALUES (?, ?)", (name, "NIFTY50"))
    return conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()["id"]


def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return cleaned[:80] or "source"


def get_video_id(url: str) -> str | None:
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtube.com"):
        return parse_qs(parsed.query).get("v", [None])[0]
    return None


def download_url(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return True
    except Exception:
        return False


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        texts: List[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                texts.append(text)
        return "\n".join(texts)
    except Exception:
        return ""


def extract_transcript_from_video(video_url: str) -> str:
    video_id = get_video_id(video_url)
    if not video_id:
        return ""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
        return " ".join(item.get("text", "") for item in transcript)
    except Exception:
        return ""


def chunk_text(text: str, chunk_size: int = 220) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    words = cleaned.split()
    chunks: List[str] = []
    for index in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[index:index + chunk_size]))
    return chunks


def infer_tags(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for tag, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(tag)
    if not found:
        return ["general"]
    return found


def build_citation(company_name: str, title: str, source_type: str, reference: str) -> str:
    normalized_type = (source_type or "").upper()
    if normalized_type in {"YOUTUBE", "VIDEO"}:
        marker = "video timestamp"
    elif reference and reference.lower().startswith("page"):
        marker = "PDF page"
    elif reference and reference.lower().startswith("p") and reference[1:].isdigit():
        marker = "PDF page"
    else:
        marker = "source reference"

    reference_text = reference.strip() if reference else "source"
    return f"{company_name} :: {title} ({marker}: {reference_text})"


def format_timestamp(seconds: float) -> str:
    total_seconds = int(float(seconds))
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_pdf_pages(pdf_path: Path) -> List[str]:
    try:
        reader = PdfReader(str(pdf_path))
        pages: List[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
        return pages
    except Exception:
        return []


def extract_transcript_segments(video_url: str) -> List[Dict[str, Any]]:
    video_id = get_video_id(video_url)
    if not video_id:
        return []
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
        return [{"text": item.get("text", "").strip(), "start": item.get("start", 0)} for item in transcript if item.get("text", "").strip()]
    except Exception:
        return []


def generate_answer(question: str, evidence: Dict[str, Any]) -> str:
    results = evidence.get("results", []) if isinstance(evidence, dict) else evidence
    if not results:
        return "I do not have direct evidence in the cached sources to answer that question confidently."

    best = results[0]
    citation = best.get("citation") or "the relevant source material"
    answer = f"Based on {citation}, {best.get('snippet', 'the company commentary suggests this direction')}."
    if len(results) > 1:
        answer += f" Supporting evidence also appears in {len(results) - 1} additional source(s)."
    return answer


def seed_sources_from_csv() -> None:
    if not LINKS_CSV.exists():
        return
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM sources").fetchone()["count"]
        if existing > 0:
            return

        with LINKS_CSV.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        for row in rows:
            company_name = (row.get("company") or "Unknown").strip()
            source_type = (row.get("type") or "PDF").strip()
            title = (row.get("title") or "Untitled").strip()
            url = (row.get("url") or "").strip()
            date = (row.get("date") or "").strip()
            company_id = get_company_id(conn, company_name)

            source_id = conn.execute(
                """
                INSERT INTO sources (company_id, source_type, title, url, cached_path, content, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (company_id, source_type, title, url, None, "", date),
            ).lastrowid

            content = ""
            cached_path = None
            if source_type.upper() == "BSE_PDF":
                safe_name = f"{safe_filename(company_name)}_{safe_filename(title)}.pdf"
                cached_path = CACHE_DIR / safe_name
                if download_url(url, cached_path):
                    pages = extract_pdf_pages(cached_path)
                    content = "\n".join(pages) if pages else "PDF content could not be extracted."
                else:
                    content = "BSE announcement text unavailable due to fetch failure."
            elif source_type.upper() in {"YOUTUBE", "VIDEO"}:
                segments = extract_transcript_segments(url)
                if segments:
                    content = " ".join(segment["text"] for segment in segments)
                else:
                    content = "YouTube transcript unavailable for this clip."
                cached_path = CACHE_DIR / f"{safe_filename(company_name)}_{safe_filename(title)}.txt"
                if content:
                    cached_path.write_text(content, encoding="utf-8")

            conn.execute(
                "UPDATE sources SET cached_path = ?, content = ? WHERE id = ?",
                (str(cached_path) if cached_path else None, content, source_id),
            )

            if content:
                if source_type.upper() == "BSE_PDF":
                    pages = extract_pdf_pages(cached_path) if cached_path and cached_path.exists() else []
                    if pages:
                        for page_number, page_text in enumerate(pages, start=1):
                            chunks = chunk_text(page_text, 180)
                            if not chunks:
                                chunks = [page_text]
                            for chunk in chunks:
                                reference = f"Page {page_number}"
                                tags = ",".join(infer_tags(chunk))
                                snippet = chunk[:220]
                                conn.execute(
                                    """
                                    INSERT INTO text_items (company_id, source_id, title, source_type, citation, content, snippet, tags)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        company_id,
                                        source_id,
                                        title,
                                        source_type,
                                        build_citation(company_name, title, source_type, reference),
                                        chunk,
                                        snippet,
                                        tags,
                                    ),
                                )
                    else:
                        chunks = chunk_text(content, 180)
                        if not chunks:
                            chunks = [content]
                        for chunk in chunks:
                            tags = ",".join(infer_tags(chunk))
                            snippet = chunk[:220]
                            conn.execute(
                                """
                                INSERT INTO text_items (company_id, source_id, title, source_type, citation, content, snippet, tags)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    company_id,
                                    source_id,
                                    title,
                                    source_type,
                                    build_citation(company_name, title, source_type, "source"),
                                    chunk,
                                    snippet,
                                    tags,
                                ),
                            )
                elif source_type.upper() in {"YOUTUBE", "VIDEO"}:
                    segments = extract_transcript_segments(url)
                    if segments:
                        for segment in segments:
                            segment_text = segment["text"]
                            timestamp = format_timestamp(segment["start"])
                            tags = ",".join(infer_tags(segment_text))
                            conn.execute(
                                """
                                INSERT INTO text_items (company_id, source_id, title, source_type, citation, content, snippet, tags)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    company_id,
                                    source_id,
                                    title,
                                    source_type,
                                    build_citation(company_name, title, source_type, timestamp),
                                    segment_text,
                                    segment_text[:220],
                                    tags,
                                ),
                            )
                    else:
                        chunks = chunk_text(content, 180)
                        if not chunks:
                            chunks = [content]
                        for chunk in chunks:
                            tags = ",".join(infer_tags(chunk))
                            snippet = chunk[:220]
                            conn.execute(
                                """
                                INSERT INTO text_items (company_id, source_id, title, source_type, citation, content, snippet, tags)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    company_id,
                                    source_id,
                                    title,
                                    source_type,
                                    build_citation(company_name, title, source_type, "source"),
                                    chunk,
                                    snippet,
                                    tags,
                                ),
                            )


def get_company_rows() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        companies = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
        company_list: List[Dict[str, Any]] = []
        for company in companies:
            sources = conn.execute(
                "SELECT * FROM sources WHERE company_id = ? ORDER BY date DESC, id DESC",
                (company["id"],),
            ).fetchall()
            company_list.append({
                "id": company["id"],
                "name": company["name"],
                "sector": company["sector"],
                "sources": [
                    {
                        "id": source["id"],
                        "title": source["title"],
                        "type": source["source_type"],
                        "url": source["url"],
                        "date": source["date"],
                        "cached_path": source["cached_path"],
                        "content": source["content"][:500] if source["content"] else "",
                    }
                    for source in sources
                ],
            })
        return company_list


def retrieve_relevant_chunks(question: str, limit: int = 5) -> List[Dict[str, Any]]:
    question_words = re.findall(r"[a-zA-Z0-9]+", question.lower())
    if not question_words:
        return []

    clauses = []
    for word in question_words:
        clauses.append("content LIKE ?")

    query = f"SELECT * FROM text_items WHERE {' OR '.join(clauses)} ORDER BY id DESC LIMIT ?"
    params: List[Any] = []
    for word in question_words:
        params.append(f"%{word}%")
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append({
            "company": conn.execute("SELECT name FROM companies WHERE id = ?", (row["company_id"],)).fetchone()["name"],
            "title": row["title"],
            "source_type": row["source_type"],
            "citation": row["citation"],
            "snippet": row["snippet"] or row["content"][:220],
            "tags": row["tags"].split(",") if row["tags"] else [],
        })
    return results


def get_company_sources(company_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sources WHERE company_id = ? ORDER BY date DESC, id DESC",
            (company_id,),
        ).fetchall()

    sources: List[Dict[str, Any]] = []
    for row in rows:
        company_name = conn.execute("SELECT name FROM companies WHERE id = ?", (company_id,)).fetchone()["name"]
        content = row["content"] or ""
        sources.append({
            "id": row["id"],
            "title": row["title"],
            "type": row["source_type"],
            "url": row["url"],
            "date": row["date"],
            "company": company_name,
            "content": content[:220] if content else "Source loaded successfully.",
            "cached_path": row["cached_path"],
        })
    return sources


@app.before_request
def before_request_hook():
    init_db()
    seed_sources_from_csv()


@app.route("/")
def index():
    companies = get_company_rows()
    return render_template("index.html", companies=companies)


@app.route("/api/companies")
def api_companies():
    return jsonify({"companies": get_company_rows()})


@app.route("/api/company/<int:company_id>")
def api_company_detail(company_id: int):
    company = None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        if row:
            company = {
                "id": row["id"],
                "name": row["name"],
                "sector": row["sector"],
                "sources": get_company_sources(company_id),
            }
    return jsonify({"company": company})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"answer": "Please enter a question.", "results": []})

    results = retrieve_relevant_chunks(question)
    answer = generate_answer(question, {"results": results})
    return jsonify({"answer": answer, "results": results})


if __name__ == "__main__":
    init_db()
    seed_sources_from_csv()
    app.run(debug=True, host="0.0.0.0", port=5000)
