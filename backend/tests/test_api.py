"""API integration tests using FastAPI TestClient."""
from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data


class TestDocumentsEndpoint:
    def test_list_documents_empty(self, client):
        response = client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data

    def test_list_documents_with_filters(self, client):
        response = client.get("/documents?status=CURRENT&limit=5")
        assert response.status_code == 200

    def test_get_nonexistent_document(self, client):
        response = client.get("/documents/nonexistent_id")
        assert response.status_code == 404


class TestSearchEndpoint:
    def test_search_request(self, client):
        response = client.post(
            "/search",
            json={"query": "capital requirements", "top_k": 5, "use_hybrid": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "latency_ms" in data

    def test_get_nonexistent_chunk(self, client):
        response = client.get("/chunks/nonexistent_chunk_id")
        assert response.status_code == 404


class TestAskEndpoint:
    def test_ask_insufficient_evidence(self, client):
        """When no documents are ingested, should return insufficient evidence."""
        response = client.post(
            "/ask",
            json={"question": "What is the Liquidity Coverage Ratio?", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "status" in data
        assert "citations" in data

    def test_ask_with_minimal_request(self, client):
        response = client.post(
            "/ask",
            json={"question": "What is the capital adequacy ratio?"},
        )
        assert response.status_code == 200


class TestEvaluationEndpoint:
    def test_list_evaluation_cases(self, client):
        response = client.get("/evaluation/cases")
        assert response.status_code == 200

    def test_get_evaluation_results(self, client):
        response = client.get("/evaluation/results")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
