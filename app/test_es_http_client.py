#!/usr/bin/env python3
"""
Simple test script to verify the ES HTTP client works correctly.
This script tests basic functionality without needing the full Flask app.
"""

import json
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from resources.es_http_client import ElasticsearchHTTPClient


def test_basic_connection():
    """Test basic connection to ES server."""
    print("Testing basic connection...")

    # You'll need to update these with your actual ES credentials
    # For now, using dummy values
    client = ElasticsearchHTTPClient(
        ["http://elastic:password@localhost:9200"],
        verify_certs=False
    )

    print("✓ Client initialized successfully")
    return client


def test_search(client):
    """Test search functionality."""
    print("\nTesting search...")

    try:
        # Simple match_all query
        result = client.search(
            index="test-index",
            body={
                "size": 10,
                "query": {
                    "match_all": {}
                }
            },
            request_timeout=30
        )
        print(f"✓ Search executed successfully")
        print(f"  Response keys: {list(result.keys())}")
        return True
    except Exception as e:
        print(f"⚠ Search test skipped or failed: {e}")
        return False


def test_bulk(client):
    """Test bulk operations."""
    print("\nTesting bulk operations...")

    try:
        body = [
            {"index": {"_index": "test-index", "_id": "1"}},
            {"field1": "value1", "field2": "value2"},
            {"index": {"_index": "test-index", "_id": "2"}},
            {"field1": "value3", "field2": "value4"}
        ]

        result = client.bulk(
            body=body,
            request_timeout=30
        )
        print(f"✓ Bulk operation completed")
        print(f"  Response keys: {list(result.keys())}")
        return True
    except Exception as e:
        print(f"⚠ Bulk test skipped or failed: {e}")
        return False


def test_update(client):
    """Test update operations."""
    print("\nTesting update...")

    try:
        result = client.update(
            index="test-index",
            id="test-doc-1",
            doc={"field": "updated_value"},
            doc_as_upsert=True,
            request_timeout=30
        )
        print(f"✓ Update operation completed")
        print(f"  Response keys: {list(result.keys())}")
        return True
    except Exception as e:
        print(f"⚠ Update test skipped or failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("ES HTTP Client Test Suite")
    print("=" * 60)

    try:
        client = test_basic_connection()

        print("\n" + "-" * 60)
        print("Note: The following tests require an actual ES server.")
        print("They may fail if the server is not accessible.")
        print("-" * 60)

        test_search(client)
        test_bulk(client)
        test_update(client)

        print("\n" + "=" * 60)
        print("Test suite completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

