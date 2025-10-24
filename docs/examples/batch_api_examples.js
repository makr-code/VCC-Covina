/**
 * Batch Operations Vanilla JavaScript Examples
 * ============================================
 * 
 * Pure JavaScript integration for Covina Batch Operations (Phase 3)
 * No framework dependencies required
 * 
 * Features:
 * - No dependencies
 * - Browser-compatible
 * - Complete examples
 * - Error handling
 * 
 * Author: Covina System
 * Date: January 2025
 */

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  BACKEND_URL: 'http://127.0.0.1:45678',
  BATCH_ENDPOINT: 'http://127.0.0.1:45678/api/v1/batch',
  DEFAULT_TIMEOUT: 30000, // 30 seconds
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Make HTTP request with error handling
 * 
 * @param {string} url - Request URL
 * @param {object} options - Fetch options
 * @returns {Promise<object>} Response data
 */
async function makeRequest(url, options = {}) {
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}

/**
 * Format execution time
 * 
 * @param {number} ms - Milliseconds
 * @returns {string} Formatted time
 */
function formatTime(ms) {
  if (ms < 1000) {
    return `${ms.toFixed(2)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Update UI element with loading state
 * 
 * @param {string} elementId - Element ID
 * @param {boolean} loading - Loading state
 */
function setLoading(elementId, loading) {
  const element = document.getElementById(elementId);
  if (!element) return;

  if (loading) {
    element.disabled = true;
    element.dataset.originalText = element.textContent;
    element.textContent = 'Loading...';
  } else {
    element.disabled = false;
    element.textContent = element.dataset.originalText || 'Submit';
  }
}

/**
 * Show error message
 * 
 * @param {string} containerId - Container element ID
 * @param {string} message - Error message
 */
function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="error-message">
      <strong>Error:</strong> ${message}
    </div>
  `;
}

/**
 * Clear container
 * 
 * @param {string} containerId - Container element ID
 */
function clearContainer(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
}

// ============================================================================
// Batch GET: Document Retrieval
// ============================================================================

/**
 * Fetch documents using batch GET endpoint
 * 
 * @param {string[]} documentIds - Document IDs
 * @param {string[]} fields - Fields to retrieve
 * @param {boolean} includeMetadata - Include metadata
 * @returns {Promise<object>} Batch GET response
 * 
 * @example
 * const result = await batchGetDocuments(['doc1', 'doc2'], ['document_id', 'classification']);
 * console.log(`Found ${result.found} documents`);
 */
async function batchGetDocuments(documentIds, fields = null, includeMetadata = true) {
  const payload = {
    document_ids: documentIds,
    fields: fields,
    include_metadata: includeMetadata,
  };

  return await makeRequest(`${CONFIG.BATCH_ENDPOINT}/get`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Example 1: Dashboard Loading
 * 
 * Load 50 recent documents for dashboard display
 */
async function exampleDashboardLoading() {
  console.log('\n=== Example 1: Dashboard Loading ===\n');

  const buttonId = 'dashboardLoadBtn';
  const containerId = 'dashboardResults';

  setLoading(buttonId, true);
  clearContainer(containerId);

  try {
    // Generate recent document IDs
    const recentDocIds = Array.from({ length: 50 }, (_, i) =>
      `doc_${i.toString().padStart(4, '0')}`
    );

    console.log(`Loading ${recentDocIds.length} documents...`);

    const startTime = performance.now();
    const result = await batchGetDocuments(recentDocIds, [
      'document_id',
      'classification',
      'file_path',
      'quality_score',
    ]);
    const endTime = performance.now();

    console.log(`✅ Found ${result.found} documents`);
    console.log(`⏱️  Execution time: ${formatTime(endTime - startTime)}`);
    console.log(`📊 Performance note: ${result.performance_note}`);

    // Display results
    displayDashboardResults(containerId, result);
  } catch (error) {
    console.error('❌ Dashboard loading failed:', error);
    showError(containerId, error.message);
  } finally {
    setLoading(buttonId, false);
  }
}

/**
 * Display dashboard results in UI
 * 
 * @param {string} containerId - Container element ID
 * @param {object} result - Batch GET result
 */
function displayDashboardResults(containerId, result) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let html = `
    <div class="results-summary">
      <h3>Dashboard Documents</h3>
      <p>
        Found <strong>${result.found}</strong> documents in 
        <strong>${formatTime(result.execution_time_ms)}</strong>
      </p>
      <p class="performance-note">${result.performance_note}</p>
    </div>
    <ul class="document-list">
  `;

  result.documents.forEach((doc) => {
    html += `
      <li class="document-item">
        <div class="doc-id">${doc.document_id}</div>
        <div class="doc-classification">${doc.classification}</div>
        <div class="doc-path">${doc.file_path}</div>
        ${
          doc.quality_score
            ? `<div class="doc-quality">Quality: ${doc.quality_score.toFixed(2)}</div>`
            : ''
        }
      </li>
    `;
  });

  html += '</ul>';
  container.innerHTML = html;
}

// ============================================================================
// Batch EXISTS: Existence Checks
// ============================================================================

/**
 * Check document existence using batch EXISTS endpoint
 * 
 * @param {string[]} documentIds - Document IDs to check
 * @returns {Promise<object>} Batch EXISTS response
 * 
 * @example
 * const result = await batchCheckExists(['doc1', 'doc2', 'fake_id']);
 * console.log(result.exists); // { doc1: true, doc2: true, fake_id: false }
 */
async function batchCheckExists(documentIds) {
  const payload = {
    document_ids: documentIds,
  };

  return await makeRequest(`${CONFIG.BATCH_ENDPOINT}/exists`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Example 2: Validate Upload References
 * 
 * Check if all referenced documents exist before upload
 */
async function exampleValidateReferences() {
  console.log('\n=== Example 2: Validate Upload References ===\n');

  const buttonId = 'validateReferencesBtn';
  const containerId = 'validationResults';

  setLoading(buttonId, true);
  clearContainer(containerId);

  try {
    // Simulate new document with 50 references
    const references = Array.from({ length: 50 }, (_, i) =>
      `doc_${i.toString().padStart(4, '0')}`
    );

    // Add some fake IDs to simulate missing references
    references.push('fake_doc_001', 'fake_doc_002', 'fake_doc_003');

    console.log(`Validating ${references.length} references...`);

    const startTime = performance.now();
    const result = await batchCheckExists(references);
    const endTime = performance.now();

    const missingRefs = Object.entries(result.exists)
      .filter(([id, exists]) => !exists)
      .map(([id]) => id);

    console.log(`✅ Found ${result.found} valid references`);
    console.log(`❌ Missing ${result.missing} references: ${missingRefs.join(', ')}`);
    console.log(`⏱️  Execution time: ${formatTime(endTime - startTime)}`);

    // Display results
    displayValidationResults(containerId, result, missingRefs);
  } catch (error) {
    console.error('❌ Validation failed:', error);
    showError(containerId, error.message);
  } finally {
    setLoading(buttonId, false);
  }
}

/**
 * Display validation results in UI
 * 
 * @param {string} containerId - Container element ID
 * @param {object} result - Batch EXISTS result
 * @param {string[]} missingRefs - Missing reference IDs
 */
function displayValidationResults(containerId, result, missingRefs) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const canUpload = missingRefs.length === 0;

  let html = `
    <div class="results-summary ${canUpload ? 'success' : 'warning'}">
      <h3>Reference Validation</h3>
      <p>
        Found: <strong>${result.found}</strong> | 
        Missing: <strong>${result.missing}</strong> | 
        Execution time: <strong>${formatTime(result.execution_time_ms)}</strong>
      </p>
      <p class="upload-status">
        ${
          canUpload
            ? '✅ All references exist. Upload can proceed.'
            : '❌ Missing references. Upload blocked.'
        }
      </p>
    </div>
  `;

  if (missingRefs.length > 0) {
    html += `
      <div class="missing-references">
        <h4>Missing References:</h4>
        <ul>
          ${missingRefs.map((id) => `<li>${id}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  container.innerHTML = html;
}

// ============================================================================
// Batch SEARCH: Semantic Search
// ============================================================================

/**
 * Perform batch semantic search
 * 
 * @param {string[]} queries - Search queries
 * @param {number} topK - Number of results per query
 * @param {number} threshold - Similarity threshold
 * @returns {Promise<object>} Batch SEARCH response
 * 
 * @example
 * const result = await batchSearch(['Vertrag', 'Rechnung'], 5, 0.7);
 * result.results.forEach(r => console.log(`${r.query}: ${r.count} matches`));
 */
async function batchSearch(queries, topK = 5, threshold = 0.7) {
  const payload = {
    queries: queries,
    top_k: topK,
    similarity_threshold: threshold,
  };

  return await makeRequest(`${CONFIG.BATCH_ENDPOINT}/search`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Example 3: Faceted Search
 * 
 * Search multiple categories simultaneously
 */
async function exampleFacetedSearch() {
  console.log('\n=== Example 3: Faceted Search ===\n');

  const buttonId = 'facetedSearchBtn';
  const containerId = 'searchResults';

  setLoading(buttonId, true);
  clearContainer(containerId);

  try {
    const categories = [
      'VERTRAG contract agreement',
      'RECHNUNG invoice billing',
      'DSGVO GDPR compliance',
      'URTEIL court judgment',
      'GESETZ law legislation',
    ];

    console.log(`Searching ${categories.length} categories...`);

    const startTime = performance.now();
    const result = await batchSearch(categories, 5, 0.7);
    const endTime = performance.now();

    console.log(`✅ Total queries: ${result.total_queries}`);
    console.log(`📊 Total results: ${result.total_results}`);
    console.log(`⏱️  Execution time: ${formatTime(endTime - startTime)}`);

    result.results.forEach((r) => {
      console.log(`  - "${r.query}": ${r.count} matches`);
    });

    // Display results
    displaySearchResults(containerId, result);
  } catch (error) {
    console.error('❌ Faceted search failed:', error);
    showError(containerId, error.message);
  } finally {
    setLoading(buttonId, false);
  }
}

/**
 * Display search results in UI
 * 
 * @param {string} containerId - Container element ID
 * @param {object} result - Batch SEARCH result
 */
function displaySearchResults(containerId, result) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let html = `
    <div class="results-summary">
      <h3>Search Results</h3>
      <p>
        Total queries: <strong>${result.total_queries}</strong> | 
        Total results: <strong>${result.total_results}</strong> | 
        Execution time: <strong>${formatTime(result.execution_time_ms)}</strong>
      </p>
      <p class="performance-note">${result.performance_note}</p>
    </div>
  `;

  result.results.forEach((searchResult) => {
    html += `
      <div class="search-result-category">
        <h4>Query: "${searchResult.query}"</h4>
        <p>Matches: ${searchResult.count}</p>
    `;

    if (searchResult.error) {
      html += `<div class="error-message">${searchResult.error}</div>`;
    } else if (searchResult.matches.length > 0) {
      html += '<ul class="match-list">';
      searchResult.matches.forEach((match) => {
        html += `
          <li class="match-item">
            <div class="match-id">${match.document_id}</div>
            <div class="match-similarity">Similarity: ${match.similarity.toFixed(2)}</div>
            ${match.content ? `<div class="match-content">${match.content.substring(0, 200)}...</div>` : ''}
          </li>
        `;
      });
      html += '</ul>';
    }

    html += '</div>';
  });

  container.innerHTML = html;
}

// ============================================================================
// Example 4: Bulk Export with Progress
// ============================================================================

/**
 * Export documents with progress tracking
 * 
 * @param {string[]} documentIds - Document IDs to export
 * @param {number} chunkSize - Batch size
 * @param {Function} progressCallback - Progress callback
 * @returns {Promise<object[]>} All documents
 */
async function exportDocumentsWithProgress(documentIds, chunkSize = 200, progressCallback = null) {
  const chunks = [];
  for (let i = 0; i < documentIds.length; i += chunkSize) {
    chunks.push(documentIds.slice(i, i + chunkSize));
  }

  const allDocuments = [];
  let processedCount = 0;

  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const result = await batchGetDocuments(chunk);

    allDocuments.push(...result.documents);
    processedCount += chunk.length;

    if (progressCallback) {
      progressCallback({
        current: processedCount,
        total: documentIds.length,
        percentage: (processedCount / documentIds.length) * 100,
        chunkIndex: i + 1,
        totalChunks: chunks.length,
      });
    }
  }

  return allDocuments;
}

/**
 * Example 4: Bulk Export
 * 
 * Export large dataset with progress tracking
 */
async function exampleBulkExport() {
  console.log('\n=== Example 4: Bulk Export ===\n');

  const buttonId = 'bulkExportBtn';
  const containerId = 'exportResults';
  const progressId = 'exportProgress';

  setLoading(buttonId, true);
  clearContainer(containerId);

  try {
    // Generate 1000 document IDs
    const documentIds = Array.from({ length: 1000 }, (_, i) =>
      `doc_${i.toString().padStart(4, '0')}`
    );

    console.log(`Exporting ${documentIds.length} documents...`);

    const startTime = performance.now();

    const documents = await exportDocumentsWithProgress(
      documentIds,
      200,
      (progress) => {
        const progressContainer = document.getElementById(progressId);
        if (progressContainer) {
          progressContainer.innerHTML = `
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${progress.percentage}%"></div>
            </div>
            <p>
              Progress: ${progress.current} / ${progress.total} 
              (${progress.percentage.toFixed(1)}%) | 
              Chunk ${progress.chunkIndex} / ${progress.totalChunks}
            </p>
          `;
        }
        console.log(`Progress: ${progress.percentage.toFixed(1)}%`);
      }
    );

    const endTime = performance.now();

    console.log(`✅ Exported ${documents.length} documents`);
    console.log(`⏱️  Total time: ${formatTime(endTime - startTime)}`);

    // Display results
    displayExportResults(containerId, documents, endTime - startTime);
  } catch (error) {
    console.error('❌ Bulk export failed:', error);
    showError(containerId, error.message);
  } finally {
    setLoading(buttonId, false);
  }
}

/**
 * Display export results in UI
 * 
 * @param {string} containerId - Container element ID
 * @param {object[]} documents - Exported documents
 * @param {number} executionTime - Execution time (ms)
 */
function displayExportResults(containerId, documents, executionTime) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Group by classification
  const byClassification = {};
  documents.forEach((doc) => {
    const cls = doc.classification || 'UNKNOWN';
    if (!byClassification[cls]) {
      byClassification[cls] = [];
    }
    byClassification[cls].push(doc);
  });

  let html = `
    <div class="results-summary success">
      <h3>Export Complete</h3>
      <p>
        Total documents: <strong>${documents.length}</strong> | 
        Execution time: <strong>${formatTime(executionTime)}</strong>
      </p>
    </div>
    <div class="export-statistics">
      <h4>Classification Breakdown:</h4>
      <ul>
  `;

  Object.entries(byClassification).forEach(([cls, docs]) => {
    html += `<li>${cls}: ${docs.length} documents</li>`;
  });

  html += `
      </ul>
    </div>
    <button onclick="downloadExportJSON()">Download as JSON</button>
  `;

  container.innerHTML = html;

  // Store documents for download
  window.exportedDocuments = documents;
}

/**
 * Download exported documents as JSON
 */
function downloadExportJSON() {
  if (!window.exportedDocuments) {
    alert('No exported documents available');
    return;
  }

  const json = JSON.stringify(window.exportedDocuments, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `covina_export_${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('✅ Download started');
}

// ============================================================================
// Example HTML Page
// ============================================================================

/**
 * Generate complete HTML page with all examples
 * 
 * Copy this HTML to a file and open in browser
 */
const EXAMPLE_HTML = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Covina Batch Operations - Examples</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      padding: 20px;
      background-color: #f5f5f5;
      line-height: 1.6;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      background-color: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    h1 {
      color: #333;
      margin-bottom: 20px;
      border-bottom: 3px solid #4CAF50;
      padding-bottom: 10px;
    }

    h2 {
      color: #555;
      margin-top: 30px;
      margin-bottom: 15px;
    }

    button {
      padding: 12px 24px;
      margin: 10px 5px 10px 0;
      background-color: #4CAF50;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
      transition: background-color 0.3s;
    }

    button:hover:not(:disabled) {
      background-color: #45a049;
    }

    button:disabled {
      background-color: #ccc;
      cursor: not-allowed;
    }

    .results-container {
      margin-top: 20px;
      padding: 15px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background-color: #f9f9f9;
    }

    .error-message {
      color: #d32f2f;
      padding: 15px;
      margin: 10px 0;
      background-color: #ffebee;
      border-left: 4px solid #d32f2f;
      border-radius: 4px;
    }

    .results-summary {
      padding: 15px;
      margin-bottom: 15px;
      background-color: #e3f2fd;
      border-left: 4px solid #2196F3;
      border-radius: 4px;
    }

    .results-summary.success {
      background-color: #e8f5e9;
      border-left-color: #4CAF50;
    }

    .results-summary.warning {
      background-color: #fff3e0;
      border-left-color: #FF9800;
    }

    .document-list, .match-list {
      list-style: none;
      padding: 0;
    }

    .document-item, .match-item {
      padding: 10px;
      margin: 5px 0;
      background-color: white;
      border: 1px solid #ddd;
      border-radius: 4px;
    }

    .progress-bar {
      width: 100%;
      height: 30px;
      background-color: #e0e0e0;
      border-radius: 15px;
      overflow: hidden;
      margin: 10px 0;
    }

    .progress-fill {
      height: 100%;
      background-color: #4CAF50;
      transition: width 0.3s;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Covina Batch Operations - Examples</h1>
    
    <h2>Example 1: Dashboard Loading</h2>
    <button id="dashboardLoadBtn" onclick="exampleDashboardLoading()">
      Load Dashboard (50 docs)
    </button>
    <div id="dashboardResults" class="results-container"></div>

    <h2>Example 2: Validate Upload References</h2>
    <button id="validateReferencesBtn" onclick="exampleValidateReferences()">
      Validate References (50 refs)
    </button>
    <div id="validationResults" class="results-container"></div>

    <h2>Example 3: Faceted Search</h2>
    <button id="facetedSearchBtn" onclick="exampleFacetedSearch()">
      Search 5 Categories
    </button>
    <div id="searchResults" class="results-container"></div>

    <h2>Example 4: Bulk Export</h2>
    <button id="bulkExportBtn" onclick="exampleBulkExport()">
      Export 1000 Documents
    </button>
    <div id="exportProgress" class="results-container"></div>
    <div id="exportResults" class="results-container"></div>
  </div>

  <script src="batch_api_examples.js"></script>
</body>
</html>
`;

// ============================================================================
// Initialization
// ============================================================================

console.log('Covina Batch Operations JavaScript Examples loaded!');
console.log('Available functions:');
console.log('  - exampleDashboardLoading()');
console.log('  - exampleValidateReferences()');
console.log('  - exampleFacetedSearch()');
console.log('  - exampleBulkExport()');
console.log('\nBackend URL:', CONFIG.BACKEND_URL);

// Export for use in browser console
if (typeof window !== 'undefined') {
  window.CovinaBatchExamples = {
    exampleDashboardLoading,
    exampleValidateReferences,
    exampleFacetedSearch,
    exampleBulkExport,
    batchGetDocuments,
    batchCheckExists,
    batchSearch,
    CONFIG,
  };
}
