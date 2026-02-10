"""
Elasticsearch HTTP Client Wrapper
This module provides a drop-in replacement for the official Elasticsearch Python client,
using direct HTTP requests instead. This allows compatibility with ES 7.x server without
requiring the elasticsearch-py library dependency.
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, quote

logger = logging.getLogger('debug-log')


class ElasticsearchHTTPClient:
    """
    A lightweight Elasticsearch client that uses HTTP requests to communicate with ES server.
    Mimics the interface of elasticsearch.Elasticsearch for drop-in compatibility.
    """

    def __init__(self, hosts: List[str], verify_certs: bool = True, **kwargs):
        """
        Initialize the ES HTTP client.

        Args:
            hosts: List of ES connection strings (e.g., ['http://elastic:password@localhost:9200'])
            verify_certs: Whether to verify SSL certificates
            **kwargs: Additional arguments (for compatibility, mostly ignored)
        """
        if not hosts or len(hosts) == 0:
            raise ValueError("At least one host must be provided")

        # Parse the first host (assuming single node for simplicity)
        self.base_url = hosts[0].rstrip('/')
        self.verify_certs = verify_certs
        self.session = requests.Session()

        # Extract auth from URL if present
        if '@' in self.base_url:
            # URL format: http://user:pass@host:port
            protocol = self.base_url.split('://')[0]
            rest = self.base_url.split('://')[1]
            auth_part = rest.split('@')[0]
            host_part = rest.split('@')[1]
            username, password = auth_part.split(':', 1)
            self.base_url = f"{protocol}://{host_part}"
            self.session.auth = (username, password)

        logger.info(f"Initialized ElasticsearchHTTPClient with base URL: {self.base_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        body: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the ES server.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            body: Request body (will be JSON-encoded)
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Response JSON as dictionary

        Raises:
            requests.RequestException: On HTTP errors
        """
        url = urljoin(self.base_url, endpoint)
        headers = {'Content-Type': 'application/json'}

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=body,
                params=params,
                headers=headers,
                timeout=timeout,
                verify=self.verify_certs
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"ES HTTP request failed: {method} {url} - {str(e)}")
            raise

    def search(
        self,
        index: Optional[str] = None,
        body: Optional[Dict] = None,
        request_timeout: Optional[int] = None,
        ignore_unavailable: bool = False,
        routing: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a search query.

        Args:
            index: Index name(s) to search
            body: Query body
            request_timeout: Timeout in seconds
            ignore_unavailable: Whether to ignore unavailable indices
            routing: Routing value
            **kwargs: Additional parameters for compatibility

        Returns:
            Search results dictionary
        """
        endpoint = f"/{index}/_search" if index else "/_search"

        params = {}
        if ignore_unavailable:
            params['ignore_unavailable'] = 'true'
        if routing:
            params['routing'] = routing

        return self._make_request(
            method='POST',
            endpoint=endpoint,
            body=body,
            params=params,
            timeout=request_timeout
        )

    def msearch(
        self,
        body: Union[List, str],
        request_timeout: Optional[int] = None,
        index: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute multiple search queries in a single request.

        Args:
            body: List of queries or newline-delimited JSON string
            request_timeout: Timeout in seconds
            index: Default index for queries
            **kwargs: Additional parameters

        Returns:
            Multi-search results dictionary
        """
        endpoint = f"/{index}/_msearch" if index else "/_msearch"

        # Convert body to newline-delimited JSON format if it's a list
        if isinstance(body, list):
            ndjson_body = '\n'.join(json.dumps(item) for item in body) + '\n'
        else:
            ndjson_body = body

        # msearch requires newline-delimited JSON, not regular JSON
        url = urljoin(self.base_url, endpoint)
        headers = {'Content-Type': 'application/x-ndjson'}

        response = self.session.post(
            url=url,
            data=ndjson_body,
            headers=headers,
            timeout=request_timeout,
            verify=self.verify_certs
        )
        response.raise_for_status()
        return response.json()

    def mget(
        self,
        body: Dict,
        index: Optional[str] = None,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get multiple documents by ID.

        Args:
            body: Request body with document IDs
            index: Index name
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Multi-get results dictionary
        """
        endpoint = f"/{index}/_mget" if index else "/_mget"

        return self._make_request(
            method='POST',
            endpoint=endpoint,
            body=body,
            timeout=request_timeout
        )

    def update(
        self,
        index: str,
        id: str,
        doc: Optional[Dict] = None,
        body: Optional[Dict] = None,
        doc_as_upsert: bool = False,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a document.

        Args:
            index: Index name
            id: Document ID
            doc: Document to update (simplified parameter)
            body: Request body (alternative to doc)
            doc_as_upsert: Create document if it doesn't exist
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Update result dictionary
        """
        endpoint = f"/{index}/_update/{quote(str(id))}"

        # Build request body
        if body is None:
            body = {}
        if doc is not None:
            body['doc'] = doc
        if doc_as_upsert:
            body['doc_as_upsert'] = True

        return self._make_request(
            method='POST',
            endpoint=endpoint,
            body=body,
            timeout=request_timeout
        )

    def bulk(
        self,
        body: Union[List, str],
        index: Optional[str] = None,
        pipeline: Optional[str] = None,
        refresh: Optional[str] = None,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform bulk operations.

        Args:
            body: List of operations or newline-delimited JSON string
            index: Default index
            pipeline: Ingest pipeline to use
            refresh: Refresh policy ('true', 'false', 'wait_for')
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Bulk operation results dictionary
        """
        endpoint = f"/{index}/_bulk" if index else "/_bulk"

        params = {}
        if pipeline:
            params['pipeline'] = pipeline
        if refresh:
            params['refresh'] = refresh

        # Convert body to newline-delimited JSON format if it's a list
        if isinstance(body, list):
            ndjson_body = '\n'.join(json.dumps(item) for item in body) + '\n'
        else:
            ndjson_body = body

        # Bulk API requires newline-delimited JSON
        url = urljoin(self.base_url, endpoint)
        headers = {'Content-Type': 'application/x-ndjson'}

        response = self.session.post(
            url=url,
            data=ndjson_body,
            headers=headers,
            params=params,
            timeout=request_timeout,
            verify=self.verify_certs
        )
        response.raise_for_status()
        return response.json()

    def delete_by_query(
        self,
        index: str,
        body: Dict,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Delete documents matching a query.

        Args:
            index: Index name
            body: Query body
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Delete result dictionary
        """
        endpoint = f"/{index}/_delete_by_query"

        return self._make_request(
            method='POST',
            endpoint=endpoint,
            body=body,
            timeout=request_timeout
        )

    def index(
        self,
        index: str,
        body: Dict,
        id: Optional[str] = None,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Index a document.

        Args:
            index: Index name
            body: Document body
            id: Document ID (optional, will be auto-generated if not provided)
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Index result dictionary
        """
        if id:
            endpoint = f"/{index}/_doc/{quote(str(id))}"
            method = 'PUT'
        else:
            endpoint = f"/{index}/_doc"
            method = 'POST'

        return self._make_request(
            method=method,
            endpoint=endpoint,
            body=body,
            timeout=request_timeout
        )

    def get(
        self,
        index: str,
        id: str,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a document by ID.

        Args:
            index: Index name
            id: Document ID
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Document dictionary
        """
        endpoint = f"/{index}/_doc/{quote(str(id))}"

        return self._make_request(
            method='GET',
            endpoint=endpoint,
            timeout=request_timeout
        )

    def delete(
        self,
        index: str,
        id: str,
        request_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Delete a document by ID.

        Args:
            index: Index name
            id: Document ID
            request_timeout: Timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Delete result dictionary
        """
        endpoint = f"/{index}/_doc/{quote(str(id))}"

        return self._make_request(
            method='DELETE',
            endpoint=endpoint,
            timeout=request_timeout
        )

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

