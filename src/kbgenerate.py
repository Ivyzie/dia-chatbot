import os
import json
import argparse
import logging
from dotenv import load_dotenv
from langchain.text_splitter import MarkdownHeaderTextSplitter, TokenTextSplitter
from langchain.docstore.document import Document
import weaviate
from weaviate.auth import AuthApiKey
import concurrent.futures

from langchain_community.retrievers import WeaviateHybridSearchRetriever
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Weaviate

from uuid import uuid5, NAMESPACE_URL


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# --- Helper Functions ---

def get_weaviate_class_name(file_key: str) -> str:
    folder = os.path.basename(os.path.dirname(file_key))
    safe = "".join(c if c.isalnum() else "_" for c in folder)
    if safe[0].isdigit():
        safe = f"_{safe}"
    return f"Domain_{safe}"

def create_weaviate_client():
    """
    Create and return a local Weaviate client instance (anonymous).
    """
    logging.debug("Creating local Weaviate client")
    # default to local weaviate
    url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    client = weaviate.Client(
        url=url,
        additional_headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
        }
    )
    logging.debug(f"Local Weaviate client created against {url}")
    return client

def get_local_file_contents(file_path):
    """
    Retrieve local file contents as a UTF-8 decoded string.
    """
    logging.debug(f"Reading local file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    logging.debug("Local file contents read successfully")
    return content

def ensure_weaviate_class(client, class_name):
    """
    Check if the Weaviate class exists; if not, create it.
    This version creates a schema suitable for website information.
    """
    logging.debug(f"Ensuring Weaviate class exists: {class_name}")
    existing = client.schema.get().get("classes", [])
    existing_classes = [cls["class"] for cls in existing]
    logging.debug(f"Existing classes: {existing_classes}")
    if class_name not in existing_classes:
        schema = {
            "class": class_name,
            "description": f"Collection for {class_name} containing website KB data",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {"model": "text-embedding-3-small"}
            },
            "properties": [
                {"name": "headers", "dataType": ["text[]"], "description": "Extracted markdown headers"},
                {"name": "content", "dataType": ["text"], "description": "Main text content"},
                {"name": "category", "dataType": ["text"], "description": "FAQ section/category"}
            ]
        }
        logging.debug(f"Creating Weaviate class with schema: {schema}")
        client.schema.create_class(schema)
        logging.info(f"Created Weaviate class: {class_name}")
    else:
        logging.info(f"Weaviate class exists: {class_name}")
    return class_name

def _split_doc_token_chunks(args):
    """
    Helper function for multiprocessing: splits a single doc into token chunks.
    """
    doc, max_tokens, chunk_overlap = args
    token_splitter = TokenTextSplitter(
        encoding_name="gpt2",
        chunk_size=max_tokens,
        chunk_overlap=chunk_overlap,
    )
    sub_chunks = token_splitter.split_text(doc.page_content)
    # Return tuples of (text, metadata)
    return [(sub_text, doc.metadata) for sub_text in sub_chunks]

def split_markdown_by_headers_and_token_limit(text: str, max_tokens: int = 1536, chunk_overlap: int = 0):
    """
    Split markdown text into smaller chunks based on Markdown headers and token limits.
    Each chunk retains header metadata. Uses multiprocessing for speed.
    """
    logging.debug("Splitting markdown text by headers")
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header1"),
            ("##", "Header2"),
            ("###", "Header3"),
            ("####", "Header4")
        ]
    )
    header_docs = header_splitter.split_text(text)
    logging.debug(f"Header split produced {len(header_docs)} document(s)")

    # Prepare arguments for multiprocessing
    args = [(doc, max_tokens, chunk_overlap) for doc in header_docs]

    final_docs = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for result in executor.map(_split_doc_token_chunks, args):
            for sub_text, metadata in result:
                final_docs.append(Document(page_content=sub_text, metadata=metadata))
    logging.debug(f"Total final documents count: {len(final_docs)}")
    return final_docs

def insert_markdown_docs(client, docs, class_name):
    client.batch.configure(batch_size=100, dynamic=True, timeout_retries=3)
    with client.batch as batch:
        for doc in docs:
            category = doc.metadata.get("Header1", "Uncategorised")
            data_obj = {
                "content": doc.page_content,
                "headers": list(doc.metadata.values()),
                "category": category
            }
            uid = uuid5(NAMESPACE_URL, doc.page_content)
            try:
                batch.add_data_object(data_obj, class_name, uuid=uid)
            except Exception as e:
                logging.error(f"Chunk insert failed: {e}")

def process_local_file_and_store(file_path, override_class: str | None = None):
    """
    Process a markdown file from local disk and store its content in Weaviate.
    This function assumes that the file contains website-related markdown content.
    """
    logging.debug(f"Starting processing for local file: {file_path}")
    client = create_weaviate_client()
    content = get_local_file_contents(file_path)
    # allow override from CLI
    class_name = override_class or get_weaviate_class_name(file_path)
    logging.debug("Processing markdown content")
    docs = split_markdown_by_headers_and_token_limit(content)
    insert_markdown_docs(client, docs, class_name)
    logging.debug("Completed processing for local file")

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

# --- Main Execution ---
def main():
    logging.debug("Starting main execution")
    parser = argparse.ArgumentParser(
        description="Process scraped markdown content from local folder and store it in Weaviate for chatbot KB."
    )
    parser.add_argument(
        "--dir", type=str, required=True,
        help="The directory name under 'scraped_content' (e.g., ASKedu_2502270001)"
    )
    parser.add_argument(
        "--class-name", dest="class_name", type=str, default=None,
        help="Optional override for Weaviate class name"
    )
    args = parser.parse_args()

    # Remove "uploads/" if present in the directory argument
    directory = args.dir.replace("uploads/", "")
    # Construct the file path based on the sanitized directory argument.
    file_path = os.path.join("scraped_content", directory, "content.md")
    logging.info(f"Processing local file: {file_path}")
    process_local_file_and_store(file_path, args.class_name)
    logging.debug("Main execution complete")

if __name__ == "__main__":
    main()
