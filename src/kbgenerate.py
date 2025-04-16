import os
import json
import argparse
import logging
from dotenv import load_dotenv
from langchain.text_splitter import MarkdownHeaderTextSplitter, TokenTextSplitter
from langchain.docstore.document import Document
import weaviate
from weaviate.auth import AuthApiKey

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# --- Helper Functions ---

def get_weaviate_class_name(file_key):
    """
    Derive the Weaviate class name from the file key.
    For our website KB ingestion, we always use a Domain class.
    """
    logging.debug(f"Extracting Weaviate class name from file_key: {file_key}")
    parts = file_key.split(os.sep)
    if len(parts) >= 3:
        folder = parts[-2]
        class_name = f"Domain_{folder}"
        logging.debug(f"Determined class name: {class_name}")
        return class_name
    logging.debug("Insufficient parts in file_key; defaulting to 'DefaultClass'")
    return "DefaultClass"

def create_weaviate_client():
    """
    Create and return a Weaviate client instance.
    """
    logging.debug("Creating Weaviate client")
    client = weaviate.Client(
        url=os.getenv('WEAVIATE_URL'),
        auth_client_secret=AuthApiKey(api_key=os.getenv('WEAVIATE_API_KEY')),
        additional_headers={
            "X-OpenAI-Api-Key": os.getenv('OPENAI_API_KEY')
        }
    )
    logging.debug("Weaviate client created successfully")
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
                {"name": "metadata", "dataType": ["text[]"], "description": "Generated metadata tags"}
            ]
        }
        logging.debug(f"Creating Weaviate class with schema: {schema}")
        client.schema.create_class(schema)
        logging.info(f"Created Weaviate class: {class_name}")
    else:
        logging.info(f"Weaviate class exists: {class_name}")
    return class_name

def split_markdown_by_headers_and_token_limit(text: str, max_tokens: int = 1536, chunk_overlap: int = 0):
    """
    Split markdown text into smaller chunks based on Markdown headers and token limits.
    Each chunk retains header metadata.
    """
    logging.debug("Splitting markdown text by headers")
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header1"),
            ("##", "Header2"),
            ("###", "Header3"),
        ]
    )
    header_docs = header_splitter.split_text(text)
    logging.debug(f"Header split produced {len(header_docs)} document(s)")

    token_splitter = TokenTextSplitter(
        encoding_name="gpt2",
        chunk_size=max_tokens,
        chunk_overlap=chunk_overlap,
    )

    final_docs = []
    for doc in header_docs:
        logging.debug("Splitting a header document into token chunks")
        sub_chunks = token_splitter.split_text(doc.page_content)
        logging.debug(f"Document split into {len(sub_chunks)} chunk(s)")
        if len(sub_chunks) == 1:
            final_docs.append(doc)
        else:
            for sub_text in sub_chunks:
                final_docs.append(Document(page_content=sub_text, metadata=doc.metadata))
    logging.debug(f"Total final documents count: {len(final_docs)}")
    return final_docs

def insert_markdown_docs(client, docs, class_name):
    """
    Insert markdown documents (with metadata) into the specified Weaviate class.
    """
    logging.debug(f"Inserting {len(docs)} markdown document(s) into Weaviate class: {class_name}")
    class_name = ensure_weaviate_class(client, class_name)
    client.batch.configure(batch_size=100)
    with client.batch as batch:
        for doc in docs:
            data_obj = {
                "content": doc.page_content,
                "headers": list(doc.metadata.values()),
                # Optionally include additional metadata if needed:
                # "metadata": [ ... ]
            }
            batch.add_data_object(data_obj, class_name)
    logging.info(f"Inserted {len(docs)} documents into {class_name}")

def process_local_file_and_store(file_path):
    """
    Process a markdown file from local disk and store its content in Weaviate.
    This function assumes that the file contains website-related markdown content.
    """
    logging.debug(f"Starting processing for local file: {file_path}")
    client = create_weaviate_client()
    content = get_local_file_contents(file_path)
    class_name = get_weaviate_class_name(file_path)
    logging.debug("Processing markdown content")
    docs = split_markdown_by_headers_and_token_limit(content)
    insert_markdown_docs(client, docs, class_name)
    logging.debug("Completed processing for local file")

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
    args = parser.parse_args()

    # Remove "uploads/" if present in the directory argument
    directory = args.dir.replace("uploads/", "")
    # Construct the file path based on the sanitized directory argument.
    file_path = os.path.join("scraped_content", directory, "content.md")
    logging.info(f"Processing local file: {file_path}")
    process_local_file_and_store(file_path)
    logging.debug("Main execution complete")

if __name__ == "__main__":
    main()
