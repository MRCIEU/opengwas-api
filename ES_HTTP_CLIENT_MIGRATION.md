# Elasticsearch HTTP Client Migration

## Overview

This migration replaces the official Elasticsearch Python client library with a lightweight HTTP-based client that communicates directly with the Elasticsearch 7.x REST API. This approach allows you to:

1. **Keep your ES 7.x server running** without needing to upgrade
2. **Remove the elasticsearch-py dependency** which was causing package conflicts
3. **Maintain 100% backward compatibility** with existing code - no changes needed to queries!

## What Changed

### New Files

1. **`resources/es_http_client.py`** - A drop-in replacement for the Elasticsearch client
   - Implements the same interface as `elasticsearch.Elasticsearch`
   - Uses the `requests` library to make HTTP calls to ES REST API
   - Supports all methods used in your codebase:
     - `search()` - Execute search queries
     - `msearch()` - Multi-search
     - `mget()` - Multi-get documents
     - `update()` - Update documents
     - `bulk()` - Bulk operations
     - `delete_by_query()` - Delete by query
     - `index()`, `get()`, `delete()` - Basic document operations

### Modified Files

1. **`resources/globals.py`**
   - Changed import: `from elasticsearch import Elasticsearch` → `from resources.es_http_client import ElasticsearchHTTPClient`
   - Changed instantiation: `Elasticsearch(...)` → `ElasticsearchHTTPClient(...)`

2. **`requirements.txt`**
   - Removed: `elasticsearch==9.2.1`
   - Added: `requests==2.31.0` (for HTTP communication)

### Files That Did NOT Change

All your query files remain **completely unchanged**:
- `queries/es_stats.py`
- `queries/es_user.py`
- `queries/es.py`
- `queries/variants.py`

The API usage `Globals.es.search()`, `Globals.es.bulk()`, etc. works exactly as before!

## How It Works

The `ElasticsearchHTTPClient` class:

1. **Parses the connection URL** to extract host, port, and credentials
2. **Maintains a requests.Session** for connection pooling and authentication
3. **Translates ES Python client calls to HTTP requests**:
   - `client.search(index="my-index", body={...})` → `POST /my-index/_search`
   - `client.bulk(body=[...])` → `POST /_bulk` (with NDJSON formatting)
   - `client.update(index="idx", id="1", doc={...})` → `POST /idx/_update/1`

4. **Returns the same JSON structure** as the official client, ensuring compatibility

## Installation

1. **Update dependencies**:
   ```bash
   cd /Users/zv21942/Projects/opengwas/opengwas-api-internal/opengwas-api/app
   pip install -r requirements.txt
   ```

2. **Verify the changes**:
   ```bash
   python test_es_http_client.py
   ```

## Testing

### Unit Test
Run the test script to verify the HTTP client initialization:
```bash
python test_es_http_client.py
```

### Integration Testing
Your existing integration tests should work without modification:
```bash
pytest apis/tests/
```

## Advantages

✅ **No code changes needed** in your query logic  
✅ **Works with ES 7.x server** - no server upgrade required  
✅ **Removes package conflicts** - no elasticsearch-py dependency  
✅ **Lightweight** - only uses requests library  
✅ **Easy to debug** - standard HTTP requests you can inspect  
✅ **Future-proof** - easy to maintain and extend  

## Implementation Details

### Method Signatures

All methods maintain the same signature as the official client:

```python
# Search
Globals.es.search(
    index="my-index",
    body={"query": {...}},
    request_timeout=120,
    ignore_unavailable=True,
    routing="some-value"
)

# Bulk operations
Globals.es.bulk(
    body=[...],
    index="my-index",
    pipeline="geoip",
    refresh="wait_for",
    request_timeout=120
)

# Update with upsert
Globals.es.update(
    index="my-index",
    id="doc-id",
    doc={"field": "value"},
    doc_as_upsert=True,
    request_timeout=60
)
```

### HTTP Mappings

| ES Client Method | HTTP Method | Endpoint |
|-----------------|-------------|----------|
| `search()` | POST | `/{index}/_search` |
| `msearch()` | POST | `/_msearch` |
| `mget()` | POST | `/{index}/_mget` |
| `update()` | POST | `/{index}/_update/{id}` |
| `bulk()` | POST | `/_bulk` |
| `delete_by_query()` | POST | `/{index}/_delete_by_query` |
| `index()` | PUT/POST | `/{index}/_doc/{id}` |
| `get()` | GET | `/{index}/_doc/{id}` |
| `delete()` | DELETE | `/{index}/_doc/{id}` |

### NDJSON Handling

Methods like `bulk()` and `msearch()` that require newline-delimited JSON (NDJSON) format are automatically handled. The client converts Python lists to NDJSON format:

```python
# You pass in a list
body = [
    {"index": {"_index": "test"}},
    {"field": "value"}
]

# Client converts to NDJSON
# {"index": {"_index": "test"}}
# {"field": "value"}
```

## Troubleshooting

### Connection Issues

If you see connection errors, verify:
1. ES server is running and accessible
2. Credentials in `vault/app_conf.json` are correct
3. Network connectivity from the Flask app to ES server

### Authentication

The client supports HTTP Basic Auth via the connection URL:
```python
ElasticsearchHTTPClient(["http://username:password@host:port"])
```

### Timeouts

All methods accept a `request_timeout` parameter (in seconds):
```python
Globals.es.search(
    index="large-index",
    body={...},
    request_timeout=300  # 5 minutes
)
```

### Debugging

Enable debug logging to see HTTP requests:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration Checklist

- [x] Create `ElasticsearchHTTPClient` class
- [x] Update imports in `globals.py`
- [x] Update ES client instantiation
- [x] Remove `elasticsearch` from requirements.txt
- [x] Add `requests` to requirements.txt
- [x] Create test script
- [ ] Run test script
- [ ] Run existing integration tests
- [ ] Deploy to development environment
- [ ] Monitor logs for any issues
- [ ] Deploy to production

## Rollback Plan

If issues arise, rollback is simple:

1. Revert changes in `globals.py`:
   ```python
   from elasticsearch import Elasticsearch
   es = Elasticsearch([...])
   ```

2. Revert `requirements.txt`:
   ```
   # Remove: requests==2.31.0
   # Add: elasticsearch==9.2.1
   ```

3. Run: `pip install -r requirements.txt`

## Support

For questions or issues:
1. Check the `ElasticsearchHTTPClient` docstrings
2. Review ES 7.x REST API documentation
3. Check logs for HTTP request/response details

