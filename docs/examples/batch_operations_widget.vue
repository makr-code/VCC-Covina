<!--
  Batch Operations Vue Component
  ==============================
  
  Vue.js integration for Covina Batch Operations (Phase 3)
  
  Features:
  - Reactive data binding
  - Composition API
  - Error handling
  - Performance tracking
  
  Author: Covina System
  Date: January 2025
-->

<template>
  <div class="batch-operations-container">
    <!-- Dashboard Widget -->
    <section class="dashboard-widget">
      <h2>Document Dashboard</h2>
      <button @click="loadDashboard" :disabled="dashboardLoading">
        {{ dashboardLoading ? 'Loading...' : 'Refresh Dashboard' }}
      </button>

      <div v-if="dashboardError" class="error">
        Error: {{ dashboardError }}
      </div>

      <div v-if="dashboardDocuments.length > 0" class="dashboard-content">
        <p>
          Loaded {{ dashboardDocuments.length }} documents in {{ dashboardPerformanceMs }}ms
        </p>
        <ul>
          <li v-for="doc in dashboardDocuments" :key="doc.document_id">
            <strong>{{ doc.classification }}</strong>: {{ doc.file_path }}
            <span v-if="doc.quality_score" class="quality">
              (Quality: {{ doc.quality_score.toFixed(2) }})
            </span>
          </li>
        </ul>
      </div>
    </section>

    <!-- Existence Checker Widget -->
    <section class="existence-checker-widget">
      <h2>Check Document Existence</h2>
      <textarea
        v-model="existenceInput"
        placeholder="Enter document IDs (comma-separated)"
        rows="5"
        cols="50"
      ></textarea>
      <button @click="checkExistence" :disabled="existenceLoading">
        {{ existenceLoading ? 'Checking...' : 'Check Existence' }}
      </button>

      <div v-if="existenceError" class="error">
        Error: {{ existenceError }}
      </div>

      <div v-if="Object.keys(existenceMap).length > 0" class="existence-results">
        <h3>Results</h3>
        <ul>
          <li
            v-for="(exists, docId) in existenceMap"
            :key="docId"
            :class="{ found: exists, notFound: !exists }"
          >
            {{ docId }}: {{ exists ? '✅ Exists' : '❌ Not Found' }}
          </li>
        </ul>
      </div>
    </section>

    <!-- Multi-Search Widget -->
    <section class="multi-search-widget">
      <h2>Multi-Query Search</h2>
      <textarea
        v-model="searchQueriesInput"
        placeholder="Enter queries (one per line)"
        rows="5"
        cols="50"
      ></textarea>
      <div class="search-options">
        <label>
          Top K:
          <input v-model.number="searchTopK" type="number" min="1" max="20" />
        </label>
        <label>
          Similarity Threshold:
          <input
            v-model.number="searchThreshold"
            type="number"
            min="0"
            max="1"
            step="0.1"
          />
        </label>
      </div>
      <button @click="performSearch" :disabled="searchLoading">
        {{ searchLoading ? 'Searching...' : 'Search' }}
      </button>

      <div v-if="searchError" class="error">
        Error: {{ searchError }}
      </div>

      <div v-if="searchResults.length > 0" class="search-results">
        <h3>Search Results</h3>
        <div v-for="(result, index) in searchResults" :key="index" class="search-result">
          <h4>Query: "{{ result.query }}"</h4>
          <p>Matches: {{ result.count }}</p>
          <div v-if="result.error" class="error">
            Error: {{ result.error }}
          </div>
          <ul v-if="result.matches.length > 0">
            <li v-for="(match, i) in result.matches" :key="i">
              <strong>{{ match.document_id }}</strong> (similarity:
              {{ match.similarity.toFixed(2) }})
              <div v-if="match.content" class="match-content">
                {{ match.content.substring(0, 200) }}...
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

// ============================================================================
// Type Definitions
// ============================================================================

interface Document {
  document_id: string;
  file_path: string;
  classification: string;
  content_length?: number;
  quality_score?: number;
  created_at?: string;
  processing_status?: string;
  [key: string]: any;
}

interface SearchResult {
  query: string;
  matches: SearchMatch[];
  count: number;
  error?: string;
}

interface SearchMatch {
  document_id: string;
  similarity: number;
  content?: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// Configuration
// ============================================================================

const BACKEND_URL = 'http://127.0.0.1:45678';
const BATCH_ENDPOINT = `${BACKEND_URL}/api/v1/batch`;

// ============================================================================
// Dashboard State
// ============================================================================

const dashboardDocuments = ref<Document[]>([]);
const dashboardLoading = ref(false);
const dashboardError = ref<string | null>(null);
const dashboardPerformanceMs = ref(0);

async function loadDashboard() {
  dashboardLoading.value = true;
  dashboardError.value = null;

  try {
    // Generate recent document IDs (example: 50 documents)
    const recentDocIds = Array.from({ length: 50 }, (_, i) =>
      `doc_${i.toString().padStart(4, '0')}`
    );

    const payload = {
      document_ids: recentDocIds,
      fields: ['document_id', 'classification', 'file_path', 'quality_score'],
      include_metadata: true,
    };

    const response = await fetch(`${BATCH_ENDPOINT}/get`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    dashboardDocuments.value = data.documents;
    dashboardPerformanceMs.value = data.execution_time_ms;
  } catch (err) {
    dashboardError.value = err instanceof Error ? err.message : 'Unknown error';
    dashboardDocuments.value = [];
  } finally {
    dashboardLoading.value = false;
  }
}

// ============================================================================
// Existence Checker State
// ============================================================================

const existenceInput = ref('');
const existenceMap = ref<Record<string, boolean>>({});
const existenceLoading = ref(false);
const existenceError = ref<string | null>(null);

async function checkExistence() {
  if (!existenceInput.value.trim()) {
    existenceError.value = 'Please enter at least one document ID';
    return;
  }

  existenceLoading.value = true;
  existenceError.value = null;

  try {
    const documentIds = existenceInput.value
      .split(',')
      .map((id) => id.trim())
      .filter((id) => id);

    const payload = {
      document_ids: documentIds,
    };

    const response = await fetch(`${BATCH_ENDPOINT}/exists`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    existenceMap.value = data.exists;
  } catch (err) {
    existenceError.value = err instanceof Error ? err.message : 'Unknown error';
    existenceMap.value = {};
  } finally {
    existenceLoading.value = false;
  }
}

// ============================================================================
// Multi-Search State
// ============================================================================

const searchQueriesInput = ref('Vertrag\nRechnung\nDSGVO');
const searchTopK = ref(5);
const searchThreshold = ref(0.7);
const searchResults = ref<SearchResult[]>([]);
const searchLoading = ref(false);
const searchError = ref<string | null>(null);

async function performSearch() {
  if (!searchQueriesInput.value.trim()) {
    searchError.value = 'Please enter at least one search query';
    return;
  }

  searchLoading.value = true;
  searchError.value = null;

  try {
    const queries = searchQueriesInput.value
      .split('\n')
      .map((q) => q.trim())
      .filter((q) => q);

    const payload = {
      queries,
      top_k: searchTopK.value,
      similarity_threshold: searchThreshold.value,
    };

    const response = await fetch(`${BATCH_ENDPOINT}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    searchResults.value = data.results;
  } catch (err) {
    searchError.value = err instanceof Error ? err.message : 'Unknown error';
    searchResults.value = [];
  } finally {
    searchLoading.value = false;
  }
}
</script>

<style scoped>
.batch-operations-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

section {
  margin-bottom: 40px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

h2 {
  margin-top: 0;
  color: #333;
}

button {
  padding: 10px 20px;
  margin: 10px 0;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

button:hover:not(:disabled) {
  background-color: #45a049;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

textarea {
  width: 100%;
  padding: 10px;
  margin: 10px 0;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
}

.error {
  color: #d32f2f;
  padding: 10px;
  margin: 10px 0;
  background-color: #ffebee;
  border: 1px solid #d32f2f;
  border-radius: 4px;
}

.dashboard-content ul,
.existence-results ul,
.search-results ul {
  list-style: none;
  padding: 0;
}

.dashboard-content li,
.existence-results li,
.search-results li {
  padding: 8px;
  margin: 5px 0;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.quality {
  color: #666;
  font-size: 14px;
  margin-left: 10px;
}

.existence-results li.found {
  border-left: 4px solid #4caf50;
}

.existence-results li.notFound {
  border-left: 4px solid #f44336;
}

.search-options {
  display: flex;
  gap: 20px;
  margin: 10px 0;
}

.search-options label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-options input {
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 80px;
}

.search-result {
  padding: 15px;
  margin: 10px 0;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.search-result h4 {
  margin-top: 0;
  color: #1976d2;
}

.match-content {
  margin-top: 5px;
  padding: 10px;
  background-color: #f5f5f5;
  border-left: 3px solid #1976d2;
  font-size: 14px;
  color: #666;
}
</style>

<!--
  ============================================================================
  Usage Instructions
  ============================================================================
  
  1. Import and use in your Vue application:
  
     import BatchOperations from './components/BatchOperations.vue';
     
     <BatchOperations />
  
  2. Customize styling:
  
     - Override CSS variables
     - Modify scoped styles
     - Add custom themes
  
  3. Extend functionality:
  
     - Add more widgets
     - Implement pagination
     - Add export capabilities
  
  4. Performance optimization:
  
     - Use computed properties for filtering
     - Implement virtual scrolling for large lists
     - Cache results in localStorage
  
  ============================================================================
  Example: Integration with Pinia Store
  ============================================================================
  
  // stores/batchOperations.ts
  import { defineStore } from 'pinia';
  
  export const useBatchOperationsStore = defineStore('batchOperations', {
    state: () => ({
      documents: [],
      loading: false,
      error: null,
    }),
    actions: {
      async loadDocuments(documentIds: string[]) {
        this.loading = true;
        this.error = null;
        
        try {
          const response = await fetch('http://127.0.0.1:45678/api/v1/batch/get', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_ids: documentIds }),
          });
          
          const data = await response.json();
          this.documents = data.documents;
        } catch (err) {
          this.error = err.message;
        } finally {
          this.loading = false;
        }
      },
    },
  });
  
  ============================================================================
  Example: Composable Function
  ============================================================================
  
  // composables/useBatchOperations.ts
  import { ref } from 'vue';
  
  export function useBatchOperations(baseUrl = 'http://127.0.0.1:45678') {
    const loading = ref(false);
    const error = ref<string | null>(null);
    
    async function batchGet(documentIds: string[]) {
      loading.value = true;
      error.value = null;
      
      try {
        const response = await fetch(`${baseUrl}/api/v1/batch/get`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document_ids: documentIds }),
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        return await response.json();
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Unknown error';
        throw err;
      } finally {
        loading.value = false;
      }
    }
    
    return {
      loading,
      error,
      batchGet,
    };
  }
  
  ============================================================================
  Example: Vue Router Integration
  ============================================================================
  
  // router/index.ts
  import { createRouter, createWebHistory } from 'vue-router';
  import BatchOperations from '@/components/BatchOperations.vue';
  
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/batch-operations',
        name: 'BatchOperations',
        component: BatchOperations,
      },
    ],
  });
  
  export default router;
-->
