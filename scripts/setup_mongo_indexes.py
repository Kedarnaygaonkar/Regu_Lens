"""
MongoDB Atlas Index Setup Script.
Creates all required indexes including:
  - Regular indexes (for filtering)
  - Atlas Search indexes (for keyword retrieval)
  - Atlas Vector Search indexes (for semantic retrieval)

Run this script once after database creation.
NOTE: Vector Search and Atlas Search indexes must be created via Atlas UI or Atlas CLI.
This script creates the regular indexes automatically and prints instructions for the Atlas indexes.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.database import setup_indexes, ping_db, get_sync_db


VECTOR_INDEX_DEFINITION = {
    "name": "chunks_vector_index",
    "type": "vectorSearch",
    "definition": {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": 1536,
                "similarity": "cosine",
            },
            {
                "type": "filter",
                "path": "document_status",
            },
            {
                "type": "filter",
                "path": "document_id",
            },
        ]
    },
}

ATLAS_SEARCH_CHUNKS_DEFINITION = {
    "name": "chunks_text_index",
    "definition": {
        "mappings": {
            "dynamic": False,
            "fields": {
                "text": {"type": "string", "analyzer": "lucene.english"},
                "section_title": {"type": "string"},
                "section_number": {"type": "string"},
                "document_status": {"type": "string"},
                "document_id": {"type": "string"},
            },
        }
    },
}

ATLAS_SEARCH_DOCS_DEFINITION = {
    "name": "documents_text_index",
    "definition": {
        "mappings": {
            "dynamic": False,
            "fields": {
                "title": {"type": "string", "analyzer": "lucene.english"},
                "summary": {"type": "string", "analyzer": "lucene.english"},
                "issuer": {"type": "string"},
                "status": {"type": "string"},
            },
        }
    },
}


def main():
    print("ReguLens — MongoDB Atlas Index Setup")
    print("=" * 50)

    # Test connection
    if not ping_db():
        print("ERROR: Cannot connect to MongoDB Atlas. Check MONGODB_URI in .env")
        sys.exit(1)

    print("[OK] Connected to MongoDB Atlas")

    # Create regular indexes
    setup_indexes()
    print("[OK] Regular MongoDB indexes created")

    # Print Atlas UI instructions
    print("\n" + "=" * 50)
    print("MANUAL STEPS REQUIRED IN MONGODB ATLAS UI:")
    print("=" * 50)

    print("\n1. CREATE ATLAS VECTOR SEARCH INDEX")
    print("   Collection: chunks")
    print("   Index Name: chunks_vector_index")
    print("   JSON Definition:")
    import json
    print(json.dumps(VECTOR_INDEX_DEFINITION["definition"], indent=2))

    print("\n2. CREATE ATLAS SEARCH INDEX (for chunks)")
    print("   Collection: chunks")
    print("   Index Name: chunks_text_index")
    print("   JSON Definition:")
    print(json.dumps(ATLAS_SEARCH_CHUNKS_DEFINITION["definition"], indent=2))

    print("\n3. CREATE ATLAS SEARCH INDEX (for documents)")
    print("   Collection: documents")
    print("   Index Name: documents_text_index")
    print("   JSON Definition:")
    print(json.dumps(ATLAS_SEARCH_DOCS_DEFINITION["definition"], indent=2))

    print("\n" + "=" * 50)
    print("Go to: https://cloud.mongodb.com → Your Cluster → Search → Create Index")
    print("=" * 50)


if __name__ == "__main__":
    main()
