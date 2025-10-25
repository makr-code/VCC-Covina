"""
Polyglot Admin - Hybrid Search Quick Reference
==============================================

Search Modes & Example Queries
-------------------------------

🤖 AUTO-DETECT MODE (Recommended)
  - Automatically selects best search mode
  - No mode selection needed
  
  Examples:
    "document"                    → keyword
    "How to process invoices?"    → semantic  
    "^DOC-[0-9]{4}$"              → regex

🧠 SEMANTIC MODE (Best for Questions)
  - Uses ChromaDB embeddings
  - Understands meaning, not just keywords
  - Best for natural language queries
  
  Examples:
    "What documents discuss payment workflows?"
    "How do I handle invoice processing?"
    "Documents related to contract management"
    
  Technical:
    - sentence-transformers embeddings
    - Cosine similarity search
    - Relevance = 1 - distance

🔤 KEYWORD MODE (Traditional Search)
  - PostgreSQL ILIKE pattern matching
  - Fast substring search
  - Case-insensitive
  
  Examples:
    "invoice contract"
    "payment processing"
    "document management"
    
  Technical:
    - WHERE title ILIKE '%query%'
    - Supports spaces, special chars

🔍 REGEX MODE (Pattern Matching)
  - PostgreSQL POSIX regex (~)
  - Powerful pattern matching
  - Case-sensitive by default
  
  Examples:
    "^[A-Z].*contract"            # Starts with capital + contains "contract"
    "DOC-[0-9]{4}"                # Document IDs (DOC-1234)
    "invoice.*[0-9]{2,4}"         # Invoice with 2-4 digit number
    "(pdf|docx)$"                 # Files ending with pdf or docx
    
  Regex Cheat Sheet:
    ^       Start of string
    $       End of string
    .       Any character
    *       0 or more
    +       1 or more
    ?       0 or 1
    [A-Z]   Any uppercase letter
    [0-9]   Any digit
    {n,m}   Between n and m occurrences
    (a|b)   a or b

Hybrid Ranking System
---------------------

Results are combined from 3 backends and ranked:

  Backend          Weight    Priority
  ────────────────────────────────────
  ChromaDB         50%       Highest (semantic relevance)
  PostgreSQL       30%       Medium (document match)
  Neo4j            20%       Lower (graph patterns)

Final Score = Σ(relevance × weight)

Example:
  Document found in PostgreSQL: relevance=0.5, weight=0.3 → score=0.15
  Chunk found in ChromaDB:      relevance=0.9, weight=0.5 → score=0.45
  Node found in Neo4j:          relevance=0.4, weight=0.2 → score=0.08
  ──────────────────────────────────────────────────────────
  Final Score: 0.15 + 0.45 + 0.08 = 0.68

Results sorted by final score (descending)

Relevance Scores by Mode
-------------------------

Mode        PostgreSQL    ChromaDB       Neo4j
────────────────────────────────────────────────
Keyword     0.5 (ILIKE)   -              0.4 (CONTAINS)
Semantic    0.3 (ts_rank) 1-distance     0.4 (CONTAINS)
Regex       0.7 (~ match) -              -

Search Workflow
---------------

1. User enters query + selects mode (or auto)
2. Mode detection (if auto):
   - Check for regex patterns (^, $, [], *, +, etc.)
   - Check for semantic indicators (3+ words, questions)
   - Default to keyword
3. Multi-backend search:
   - PostgreSQL: keyword/fuzzy/regex
   - ChromaDB: semantic similarity
   - Neo4j: graph pattern matching
4. Merge results with relevance scores
5. Apply backend weights
6. Sort by final score (desc)
7. Display top 30 results

Performance Tips
----------------

✅ DO:
  - Use semantic mode for questions/concepts
  - Use keyword mode for simple terms
  - Use regex for specific patterns
  - Let auto-detect choose for you

❌ DON'T:
  - Use regex for simple keywords (slower)
  - Use keyword mode for questions (poor results)
  - Forget to validate regex patterns (syntax errors)

Example Queries by Use Case
----------------------------

Financial Documents:
  Semantic: "What documents discuss payment workflows?"
  Keyword:  "invoice payment contract"
  Regex:    "INV-[0-9]{4,6}"

Legal Documents:
  Semantic: "Documents related to contract agreements"
  Keyword:  "contract agreement terms"
  Regex:    "^(Agreement|Contract).*[0-9]{4}$"

Technical Documents:
  Semantic: "How does the system process uploads?"
  Keyword:  "upload processing technical"
  Regex:    "API.*endpoint.*POST"

Document IDs:
  Regex:    "^DOC-[A-Z]{2}-[0-9]{4}$"  # DOC-AB-1234
  Regex:    "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"  # UUID prefix

Troubleshooting
---------------

❌ No results found:
  - Try different search mode
  - Check spelling
  - Use broader terms
  - Try semantic mode for concepts

❌ Regex syntax error:
  - Validate regex pattern first
  - Escape special chars: \. \* \+ \?
  - Test at https://regex101.com

❌ Slow search:
  - Avoid complex regex on large datasets
  - Use keyword mode for simple searches
  - Limit result count (default: 50)

Backend Distribution
--------------------

Status bar shows backend result counts:

  "Found 27 results (semantic) | PG: 12, ChromaDB: 10, Neo4j: 5"
  
  PG = PostgreSQL (relational documents)
  ChromaDB = Vector chunks (semantic similarity)
  Neo4j = Graph nodes (knowledge graph)

API Reference
-------------

SearchController.hybrid_search(query, limit=10, mode='auto')
  
  Parameters:
    query (str):  Search query
    limit (int):  Max results per backend (default: 10)
    mode (str):   Search mode ('auto', 'semantic', 'keyword', 'regex')
  
  Returns:
    {
      'query': str,
      'mode': str,
      'timestamp': float,
      'relational': List[Dict],
      'vector': List[Dict],
      'graph': List[Dict],
      'total_results': int
    }

SearchController.merge_and_rank_results(results, weights=None)
  
  Parameters:
    results (Dict): Output from hybrid_search()
    weights (Dict): Backend weights (optional)
  
  Returns:
    List[Dict] sorted by final_score (descending)

SearchController.detect_search_mode(query)
  
  Parameters:
    query (str): Search query
  
  Returns:
    str: Detected mode ('regex', 'semantic', or 'keyword')

"""
