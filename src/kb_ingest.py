"""crawl_and_ingest.py – unified crawler + ingester
------------------------------------------------
Requires:
  pip install crawl4ai weaviate-client langchain-community python-dotenv
  # plus OPENAI_API_KEY (and optional WEAVIATE_URL) in .env
Run:
  python crawl_and_ingest.py
  # then paste space‑separated URLs when prompted
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import textwrap
import json
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import List
from uuid import uuid5, NAMESPACE_URL


from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, TokenTextSplitter
from langchain_community.vectorstores import Weaviate
import weaviate

# ---------------------------------------------------------------------------
# Config & logging
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
CONTENT_MD = OUTPUT_DIR / "content.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv(SCRIPT_DIR.parent / "config" / ".env")

# ---------------------------------------------------------------------------
# Weaviate helpers
# ---------------------------------------------------------------------------

def create_weaviate_client() -> weaviate.Client:
    url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    logger.debug("Connecting to Weaviate at %s", url)
    
# I understand the risks of hardcoding the API key in the code. This key is limited to embedding only.
    OPENAI_API_KEY = "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"  
    
    return weaviate.Client(
        url=url,
        additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    )


def ensure_class(client: weaviate.Client, class_name: str):
    existing = {c["class"] for c in client.schema.get().get("classes", [])}
    if class_name in existing:
        return
    schema = {
        "class": class_name,
        "description": f"KB content for {class_name}",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {"text2vec-openai": {"model": "text-embedding-3-small"}},
        "properties": [
            {"name": "headers", "dataType": ["text[]"]},
            {"name": "content", "dataType": ["text"]},
            {"name": "category", "dataType": ["text"]},
        ],
    }
    client.schema.create_class(schema)
    logger.info("Created Weaviate class %s", class_name)

# ---------------------------------------------------------------------------
# Markdown splitting
# ---------------------------------------------------------------------------

def split_markdown(text: str, *, max_tokens: int = 1536, overlap: int = 0) -> List[Document]:
    header_splitter = MarkdownHeaderTextSplitter([
        ("#", "Header1"),
        ("##", "Header2"),
        ("###", "Header3"),
        ("####", "Header4"),
    ])
    header_docs = header_splitter.split_text(text)

    splitter = TokenTextSplitter(
        encoding_name="gpt2",
        chunk_size=max_tokens,
        chunk_overlap=overlap,
    )
    docs: List[Document] = []
    for doc in header_docs:
        for chunk in splitter.split_text(doc.page_content):
            docs.append(Document(page_content=chunk, metadata=doc.metadata))
    return docs

# ---------------------------------------------------------------------------
# Crawling
# ---------------------------------------------------------------------------

def domain_from_url(url: str) -> str:
    netloc = urllib.parse.urlparse(url).netloc
    return re.sub(r"^www\.", "", netloc).split(":")[0]  # strip www & port


async def crawl(urls: List[str]):
    config = CrawlerRunConfig(
        excluded_tags=["header", "footer", "nav", "section.article-relatives"],
        word_count_threshold=10,
        exclude_external_links=True,
        exclude_social_media_links=True,
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    logger.info("Writing raw markdown to %s", CONTENT_MD)

    async with AsyncWebCrawler() as crawler:
        with CONTENT_MD.open("w", encoding="utf-8") as fp:  # normal sync file I/O
            for url in urls:
                logger.info("Scraping %s", url)
                result = await crawler.arun(url, config=config)
                markdown = result.markdown or f"No markdown content for {url}"
                fp.write(f"## {url}\n\n{markdown}\n\n")
    logger.info("Finished scraping – combined markdown saved.")

# ---------------------------------------------------------------------------
# Ingestion pipeline per domain
# ---------------------------------------------------------------------------

def ingest_markdown(md_text: str, class_name: str):
    client = create_weaviate_client()
    ensure_class(client, class_name)

    docs = split_markdown(md_text)
    logger.info("%d chunks generated for class %s", len(docs), class_name)

    client.batch.configure(batch_size=100, dynamic=True, timeout_retries=3)
    uploaded = 0
    with client.batch as batch:
        for d in docs:
            obj = {
                "headers": list(d.metadata.values()),
                "content": d.page_content,
                "category": d.metadata.get("Header1", "Uncategorised"),
            }
            uid = uuid5(NAMESPACE_URL, d.page_content)
            batch.add_data_object(obj, class_name, uuid=uid)
            uploaded += 1
    logger.info("Uploaded %d objects to %s", uploaded, class_name)

# ---------------------------------------------------------------------------
# Save Class Name
# ---------------------------------------------------------------------------

def save_latest_class_info(class_name: str):
    """Save the latest ingested class name to a JSON file."""
    output_file = OUTPUT_DIR / "latest_class.json"
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    class_info = {
        "latest_class": class_name,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(class_info, f, indent=2)
    
    logger.info(f"Saved latest class info to {output_file}")

# ---------------------------------------------------------------------------
# Build Retriever
# ---------------------------------------------------------------------------

def build_retriever(class_name: str, category: str | None = None):
    client = create_weaviate_client()
    store  = Weaviate(
        client=client,
        index_name=class_name,
        text_key="content",
        attributes=["category", "headers"]
    )
    search_kwargs = {"k": 8}
    if category:
        search_kwargs["filters"] = {
            "path": ["category"],
            "operator": "Equal",
            "valueText": category
        }
    return store.as_retriever(search_kwargs=search_kwargs)
# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------
async def main():
    links_file = SCRIPT_DIR / "input" / "links.txt"
    urls = []
    if links_file.exists():
        with links_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):  # skip empty and comment lines
                    urls.append(line)
        print(f"Loaded {len(urls)} URLs from {links_file}")
    else:
        print("Tip: If you have many URLs, just put each on its own line in input/links.txt and rerun.")
        urls = input("Enter website URLs (space‑separated): ").strip().split()
    if not urls:
        print("No URLs provided – exiting.")
        return

    # 1) scrape all URLs to single markdown file
    await crawl(urls)
    md_text = CONTENT_MD.read_text("utf-8")

    # 2) Group URLs by domain and ingest each group into its own class
    domain_groups: dict[str, list[str]] = defaultdict(list)
    for u in urls:
        domain_groups[domain_from_url(u)].append(u)

    latest_class = None
    for domain in domain_groups:
        class_name = f"Domain_{re.sub(r'[^0-9A-Za-z]', '_', domain)}"
        ingest_markdown(md_text, class_name)
        latest_class = class_name  # Keep track of the last class processed

    # Save the latest class info to a JSON file
    if latest_class:
        save_latest_class_info(latest_class)

    logger.info("All done! Domains ingested: %s", ", ".join(domain_groups))

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl URLs and ingest into Weaviate.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")
