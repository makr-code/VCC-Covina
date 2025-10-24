/**
 * Batch API Client - TypeScript/JavaScript
 * ========================================
 * 
 * Frontend integration for Covina Batch Operations (Phase 3)
 * 
 * Features:
 * - Type-safe API client
 * - Error handling
 * - Performance tracking
 * - React hooks
 * 
 * Author: Covina System
 * Date: January 2025
 */

// ============================================================================
// Type Definitions
// ============================================================================

export interface BatchGetRequest {
  document_ids: string[];
  fields?: string[];
  include_metadata?: boolean;
}

export interface BatchGetResponse {
  success: boolean;
  documents: Document[];
  found: number;
  not_found: number;
  not_found_ids?: string[];
  execution_time_ms: number;
  performance_note: string;
}

export interface BatchExistsRequest {
  document_ids: string[];
}

export interface BatchExistsResponse {
  success: boolean;
  exists: Record<string, boolean>;
  total: number;
  found: number;
  missing: number;
  execution_time_ms: number;
  performance_note: string;
}

export interface BatchSearchRequest {
  queries: string[];
  top_k?: number;
  similarity_threshold?: number;
}

export interface BatchSearchResponse {
  success: boolean;
  results: SearchResult[];
  total_queries: number;
  total_results: number;
  execution_time_ms: number;
  performance_note: string;
}

export interface SearchResult {
  query: string;
  matches: SearchMatch[];
  count: number;
  error?: string;
}

export interface SearchMatch {
  document_id: string;
  similarity: number;
  content?: string;
  metadata?: Record<string, any>;
}

export interface Document {
  document_id: string;
  file_path: string;
  classification: string;
  content_length?: number;
  quality_score?: number;
  created_at?: string;
  processing_status?: string;
  [key: string]: any;
}

// ============================================================================
// API Client
// ============================================================================

export class CovinaBatchAPIClient {
  private baseUrl: string;
  private batchEndpoint: string;

  constructor(baseUrl: string = 'http://127.0.0.1:45678') {
    this.baseUrl = baseUrl;
    this.batchEndpoint = `${baseUrl}/api/v1/batch`;
  }

  /**
   * Batch GET: Retrieve multiple documents
   * 
   * @param request - Batch GET request
   * @returns Promise with documents
   * 
   * @example
   * const client = new CovinaBatchAPIClient();
   * const result = await client.batchGet({
   *   document_ids: ['doc1', 'doc2', 'doc3'],
   *   fields: ['document_id', 'classification'],
   *   include_metadata: true
   * });
   * console.log(`Found ${result.found} documents in ${result.execution_time_ms}ms`);
   */
  async batchGet(request: BatchGetRequest): Promise<BatchGetResponse> {
    const response = await fetch(`${this.batchEndpoint}/get`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Batch GET failed: ${error.detail || response.statusText}`);
    }

    return response.json();
  }

  /**
   * Batch EXISTS: Check document existence
   * 
   * @param request - Batch EXISTS request
   * @returns Promise with existence map
   * 
   * @example
   * const client = new CovinaBatchAPIClient();
   * const result = await client.batchExists({
   *   document_ids: ['doc1', 'doc2', 'fake_id']
   * });
   * console.log(result.exists); // { doc1: true, doc2: true, fake_id: false }
   */
  async batchExists(request: BatchExistsRequest): Promise<BatchExistsResponse> {
    const response = await fetch(`${this.batchEndpoint}/exists`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Batch EXISTS failed: ${error.detail || response.statusText}`);
    }

    return response.json();
  }

  /**
   * Batch SEARCH: Multiple semantic searches
   * 
   * @param request - Batch SEARCH request
   * @returns Promise with search results
   * 
   * @example
   * const client = new CovinaBatchAPIClient();
   * const result = await client.batchSearch({
   *   queries: ['Vertrag', 'Rechnung', 'DSGVO'],
   *   top_k: 5,
   *   similarity_threshold: 0.7
   * });
   * result.results.forEach(r => {
   *   console.log(`Query "${r.query}": ${r.count} matches`);
   * });
   */
  async batchSearch(request: BatchSearchRequest): Promise<BatchSearchResponse> {
    const response = await fetch(`${this.batchEndpoint}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Batch SEARCH failed: ${error.detail || response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get batch operations status
   * 
   * @returns Promise with status information
   */
  async getStatus(): Promise<any> {
    const response = await fetch(`${this.batchEndpoint}/status`);

    if (!response.ok) {
      throw new Error(`Status check failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// ============================================================================
// React Hooks (Optional)
// ============================================================================

import { useState, useEffect, useCallback } from 'react';

/**
 * React Hook: useBatchGet
 * 
 * @example
 * const { documents, loading, error, fetchDocuments } = useBatchGet();
 * 
 * useEffect(() => {
 *   fetchDocuments(['doc1', 'doc2', 'doc3']);
 * }, []);
 */
export function useBatchGet(baseUrl?: string) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [performanceMs, setPerformanceMs] = useState<number>(0);

  const client = new CovinaBatchAPIClient(baseUrl);

  const fetchDocuments = useCallback(async (
    documentIds: string[],
    fields?: string[]
  ) => {
    setLoading(true);
    setError(null);

    try {
      const result = await client.batchGet({
        document_ids: documentIds,
        fields,
        include_metadata: true,
      });

      setDocuments(result.documents);
      setPerformanceMs(result.execution_time_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { documents, loading, error, performanceMs, fetchDocuments };
}

/**
 * React Hook: useBatchExists
 * 
 * @example
 * const { existsMap, loading, error, checkExistence } = useBatchExists();
 * 
 * const handleCheck = async () => {
 *   const result = await checkExistence(['doc1', 'doc2']);
 *   console.log(result); // { doc1: true, doc2: false }
 * };
 */
export function useBatchExists(baseUrl?: string) {
  const [existsMap, setExistsMap] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const client = new CovinaBatchAPIClient(baseUrl);

  const checkExistence = useCallback(async (documentIds: string[]) => {
    setLoading(true);
    setError(null);

    try {
      const result = await client.batchExists({ document_ids: documentIds });
      setExistsMap(result.exists);
      return result.exists;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setExistsMap({});
      return {};
    } finally {
      setLoading(false);
    }
  }, []);

  return { existsMap, loading, error, checkExistence };
}

/**
 * React Hook: useBatchSearch
 * 
 * @example
 * const { results, loading, error, search } = useBatchSearch();
 * 
 * const handleSearch = async () => {
 *   await search(['Vertrag', 'Rechnung'], 5, 0.7);
 * };
 */
export function useBatchSearch(baseUrl?: string) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const client = new CovinaBatchAPIClient(baseUrl);

  const search = useCallback(async (
    queries: string[],
    topK: number = 5,
    threshold: number = 0.7
  ) => {
    setLoading(true);
    setError(null);

    try {
      const result = await client.batchSearch({
        queries,
        top_k: topK,
        similarity_threshold: threshold,
      });

      setResults(result.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, error, search };
}

// ============================================================================
// Example React Components
// ============================================================================

/**
 * Example: Dashboard Component
 */
export function DashboardExample() {
  const { documents, loading, error, fetchDocuments } = useBatchGet();

  useEffect(() => {
    // Load recent documents on mount
    const recentDocIds = Array.from({ length: 50 }, (_, i) => `doc_${i.toString().padStart(4, '0')}`);
    fetchDocuments(recentDocIds, ['document_id', 'classification', 'file_path', 'quality_score']);
  }, [fetchDocuments]);

  if (loading) return <div>Loading dashboard...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Document Dashboard</h1>
      <p>Loaded {documents.length} documents</p>
      <ul>
        {documents.map(doc => (
          <li key={doc.document_id}>
            {doc.classification}: {doc.file_path}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Example: Existence Checker Component
 */
export function ExistenceCheckerExample() {
  const [documentIds, setDocumentIds] = useState<string>('');
  const { existsMap, loading, error, checkExistence } = useBatchExists();

  const handleCheck = async () => {
    const ids = documentIds.split(',').map(id => id.trim());
    await checkExistence(ids);
  };

  return (
    <div>
      <h2>Check Document Existence</h2>
      <textarea
        value={documentIds}
        onChange={(e) => setDocumentIds(e.target.value)}
        placeholder="Enter document IDs (comma-separated)"
        rows={5}
        cols={50}
      />
      <button onClick={handleCheck} disabled={loading}>
        {loading ? 'Checking...' : 'Check Existence'}
      </button>

      {error && <div style={{ color: 'red' }}>Error: {error}</div>}

      {Object.keys(existsMap).length > 0 && (
        <ul>
          {Object.entries(existsMap).map(([id, exists]) => (
            <li key={id}>
              {id}: {exists ? '✅ Exists' : '❌ Not Found'}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Example: Multi-Search Component
 */
export function MultiSearchExample() {
  const [queries, setQueries] = useState<string>('Vertrag\nRechnung\nDSGVO');
  const { results, loading, error, search } = useBatchSearch();

  const handleSearch = async () => {
    const queryList = queries.split('\n').map(q => q.trim()).filter(q => q);
    await search(queryList, 5, 0.7);
  };

  return (
    <div>
      <h2>Multi-Query Search</h2>
      <textarea
        value={queries}
        onChange={(e) => setQueries(e.target.value)}
        placeholder="Enter queries (one per line)"
        rows={5}
        cols={50}
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>

      {error && <div style={{ color: 'red' }}>Error: {error}</div>}

      {results.length > 0 && (
        <div>
          {results.map((result, index) => (
            <div key={index}>
              <h3>Query: "{result.query}"</h3>
              <p>Matches: {result.count}</p>
              {result.error && <p style={{ color: 'red' }}>Error: {result.error}</p>}
              {result.matches.length > 0 && (
                <ul>
                  {result.matches.map((match, i) => (
                    <li key={i}>
                      {match.document_id} (similarity: {match.similarity.toFixed(2)})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Export
// ============================================================================

export default CovinaBatchAPIClient;
