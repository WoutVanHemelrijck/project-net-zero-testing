"""
ingest.py — Parse GSF patterns repo, embed via Voyage AI, store in ChromaDB.

Usage:
    python rag/ingest.py --source ./rag/patterns_repo --persist ./rag/chroma_store
"""

import argparse
import os
import re
import time
from pathlib import Path

import voyageai
import chromadb
from dotenv import load_dotenv

load_dotenv()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_frontmatter(content: str) -> dict:
    """Extract YAML-style frontmatter fields from a markdown file."""
    frontmatter = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_front = parts[1]
            body = parts[2].strip()
            for line in raw_front.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def extract_section(body: str, heading: str) -> str:
    """Extract the text beneath a markdown heading (e.g. '## Problem')."""
    pattern = rf"(?:^|\n)#{1,3}\s+{re.escape(heading)}\s*\n(.*?)(?=\n#{1,3}\s|\Z)"
    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def parse_pattern(filepath: Path, repo_root: Path) -> dict | None:
    """Parse a single GSF pattern markdown file into a structured dict."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(content)

    title = frontmatter.get("title", filepath.stem)
    tags_raw = frontmatter.get("tags", "")
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.strip("[]").split(",") if t.strip()]
    else:
        tags = []

    problem = extract_section(body, "Problem") or extract_section(body, "Context")
    solution = extract_section(body, "Solution") or extract_section(body, "Resolution")

    if not problem and not solution:
        # Fall back to first 500 chars of body
        problem = body[:500]

    rel_path = filepath.relative_to(repo_root).as_posix()
    url = f"https://github.com/Green-Software-Foundation/patterns/blob/main/{rel_path}"

    # Use the relative file path as the ID to guarantee uniqueness
    rel_slug = slugify(rel_path.replace("/", "-").replace(".md", ""))

    return {
        "title": title,
        "tags": tags,
        "problem": problem,
        "solution": solution,
        "full_text": content,
        "url": url,
        "id": rel_slug,
    }


# Filenames that are repo metadata, not patterns
_SKIP_STEMS = {
    "readme", "contributing", "license", "adopters", "enablement",
    "template", "pull_request_template", "code_of_conduct", "index",
    "initial-reviewer-guide", "sme-reviewer-guide", "suggested-tags",
}


def ingest(source_dir: str, persist_dir: str, batch_size: int = 5) -> None:
    source = Path(source_dir)
    md_files = [
        f for f in source.rglob("*.md")
        if f.stem.lower() not in _SKIP_STEMS
        and not any(part.startswith(".") for part in f.parts)
    ]

    if not md_files:
        print(f"No pattern .md files found under {source_dir}")
        return

    print(f"Found {len(md_files)} pattern files")

    vo = voyageai.Client()
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_or_create_collection("gsf_patterns")

    patterns = []
    for filepath in md_files:
        parsed = parse_pattern(filepath, source)
        if parsed:
            patterns.append(parsed)

    print(f"Parsed {len(patterns)} patterns")

    # Free tier: 3 RPM, 10K TPM — batch small and sleep between requests
    for batch_start in range(0, len(patterns), batch_size):
        batch = patterns[batch_start : batch_start + batch_size]

        embed_texts = [
            f"{p['problem']} {p['solution']}".strip() or p["full_text"][:1000]
            for p in batch
        ]

        result = vo.embed(embed_texts, model="voyage-code-2", input_type="document")
        embeddings = result.embeddings

        collection.upsert(
            documents=embed_texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "pattern_name": p["title"],
                    "tags": ", ".join(p["tags"]),
                    "full_text": p["full_text"],
                    "url": p["url"],
                }
                for p in batch
            ],
            ids=[p["id"] for p in batch],
        )

        end = min(batch_start + batch_size, len(patterns))
        print(f"  Ingested {batch_start + 1}–{end}: {[p['title'] for p in batch]}")

        # Respect free-tier rate limit (3 RPM) — skip sleep after last batch
        if end < len(patterns):
            time.sleep(21)

    print(f"\nDone. {len(patterns)} patterns stored in {persist_dir}")


def main():
    parser = argparse.ArgumentParser(description="Ingest GSF patterns into ChromaDB")
    parser.add_argument(
        "--source",
        default=os.getenv("PATTERNS_SOURCE_DIR", "./rag/patterns_repo"),
        help="Path to cloned GSF patterns repo",
    )
    parser.add_argument(
        "--persist",
        default=os.getenv("CHROMA_PERSIST_DIR", "./rag/chroma_store"),
        help="ChromaDB persistence directory",
    )
    args = parser.parse_args()
    ingest(args.source, args.persist)


if __name__ == "__main__":
    main()
