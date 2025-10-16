# -*- coding: utf-8 -*-
"""
Benchmark Database

SQLite-basierte Speicherung und Verwaltung von KI-Evaluation-Benchmarks,
Judge-Ergebnissen und Performance-Metriken.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
import threading
import uuid

logger = logging.getLogger(__name__)

class BenchmarkDatabase:
    """
    SQLite database for AI Judge benchmark results and analytics
    
    Features:
    - Evaluation result storage with full traceability
    - Judge performance tracking and comparison
    - Statistical analysis and reporting
    - Temporal trend analysis
    - Export and backup functionality
    """
    
    def __init__(self, db_path: str = "./data/ai_judge_benchmarks.db"):
        """Initialize benchmark database"""
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database schema
        self._initialize_schema()
        
        logger.info(f"Benchmark Database initialized: {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
            
        return self._local.connection
    
    def _initialize_schema(self):
        """Initialize database schema"""
        
        schema_sql = """
        -- Main evaluations table
        CREATE TABLE IF NOT EXISTS evaluations (
            evaluation_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            ai_answer TEXT NOT NULL,
            golden_standard_id TEXT,
            golden_standard_data TEXT, -- JSON
            context_data TEXT, -- JSON
            final_scores TEXT, -- JSON
            consensus_scores TEXT, -- JSON
            analysis_data TEXT, -- JSON
            config_used TEXT, -- JSON
            processing_time_seconds REAL DEFAULT 0.0,
            overall_score REAL DEFAULT 0.0,
            benchmark_category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Individual judge results
        CREATE TABLE IF NOT EXISTS judge_results (
            judge_result_id TEXT PRIMARY KEY,
            evaluation_id TEXT REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
            judge_model TEXT NOT NULL,
            judge_timestamp TEXT NOT NULL,
            individual_scores TEXT, -- JSON
            feedback_data TEXT, -- JSON
            confidence_scores TEXT, -- JSON
            overall_confidence REAL DEFAULT 0.0,
            compliance_score REAL,
            raw_response TEXT,
            processing_time_seconds REAL DEFAULT 0.0,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Golden standards tracking
        CREATE TABLE IF NOT EXISTS golden_standards (
            standard_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            ideal_answer TEXT,
            key_points TEXT, -- JSON array
            context_info TEXT, -- JSON
            evaluation_criteria TEXT, -- JSON array
            metadata_info TEXT, -- JSON
            version TEXT DEFAULT '1.0',
            created_by TEXT DEFAULT 'system',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Judge performance tracking
        CREATE TABLE IF NOT EXISTS judge_performance (
            performance_id TEXT PRIMARY KEY,
            judge_model TEXT NOT NULL,
            evaluation_period_start TEXT NOT NULL,
            evaluation_period_end TEXT NOT NULL,
            total_evaluations INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0.0,
            score_std_deviation REAL DEFAULT 0.0,
            average_confidence REAL DEFAULT 0.0,
            agreement_with_consensus REAL DEFAULT 0.0,
            processing_time_avg REAL DEFAULT 0.0,
            error_rate REAL DEFAULT 0.0,
            performance_metrics TEXT, -- JSON
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Benchmark comparison results
        CREATE TABLE IF NOT EXISTS benchmark_comparisons (
            comparison_id TEXT PRIMARY KEY,
            comparison_name TEXT NOT NULL,
            baseline_period_start TEXT,
            baseline_period_end TEXT,
            test_period_start TEXT,
            test_period_end TEXT,
            comparison_criteria TEXT, -- JSON
            baseline_metrics TEXT, -- JSON
            test_metrics TEXT, -- JSON
            comparison_results TEXT, -- JSON
            statistical_significance REAL,
            improvement_areas TEXT, -- JSON
            regression_areas TEXT, -- JSON
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- System performance metrics
        CREATE TABLE IF NOT EXISTS system_metrics (
            metric_id TEXT PRIMARY KEY,
            metric_timestamp TEXT NOT NULL,
            metric_type TEXT NOT NULL, -- 'latency', 'throughput', 'accuracy', etc.
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            context_info TEXT, -- JSON
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance optimization
        CREATE INDEX IF NOT EXISTS idx_evaluations_timestamp 
        ON evaluations(timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_evaluations_overall_score 
        ON evaluations(overall_score DESC, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_evaluations_category 
        ON evaluations(benchmark_category, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_judge_results_eval_id 
        ON judge_results(evaluation_id);

        CREATE INDEX IF NOT EXISTS idx_judge_results_model 
        ON judge_results(judge_model, judge_timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_golden_standards_created 
        ON golden_standards(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_judge_performance_model 
        ON judge_performance(judge_model, evaluation_period_start DESC);

        CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time 
        ON system_metrics(metric_type, metric_timestamp DESC);

        -- Full-text search for questions and answers
        CREATE VIRTUAL TABLE IF NOT EXISTS evaluations_fts USING fts5(
            evaluation_id UNINDEXED,
            question, 
            ai_answer,
            content='evaluations',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 1'
        );

        -- Triggers to maintain FTS index
        CREATE TRIGGER IF NOT EXISTS evaluations_fts_insert AFTER INSERT ON evaluations
        BEGIN
            INSERT INTO evaluations_fts(evaluation_id, question, ai_answer) 
            VALUES (new.evaluation_id, new.question, new.ai_answer);
        END;

        CREATE TRIGGER IF NOT EXISTS evaluations_fts_update AFTER UPDATE ON evaluations
        BEGIN
            UPDATE evaluations_fts SET question = new.question, ai_answer = new.ai_answer 
            WHERE evaluation_id = new.evaluation_id;
        END;

        CREATE TRIGGER IF NOT EXISTS evaluations_fts_delete AFTER DELETE ON evaluations
        BEGIN
            DELETE FROM evaluations_fts WHERE evaluation_id = old.evaluation_id;
        END;

        -- Update timestamp trigger for golden standards
        CREATE TRIGGER IF NOT EXISTS update_golden_standards_timestamp 
        AFTER UPDATE ON golden_standards
        BEGIN
            UPDATE golden_standards SET updated_at = CURRENT_TIMESTAMP 
            WHERE standard_id = NEW.standard_id;
        END;
        """
        
        try:
            with self.connection:
                self.connection.executescript(schema_sql)
            logger.info("Benchmark database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    async def store_evaluation(self, evaluation_result: Dict[str, Any]) -> bool:
        """Store complete evaluation result in database"""
        
        try:
            evaluation_id = evaluation_result.get('evaluation_id')
            if not evaluation_id:
                evaluation_id = str(uuid.uuid4())
                evaluation_result['evaluation_id'] = evaluation_id
            
            # Store main evaluation record
            eval_sql = """
            INSERT OR REPLACE INTO evaluations (
                evaluation_id, timestamp, question, ai_answer, golden_standard_id,
                golden_standard_data, context_data, final_scores, consensus_scores,
                analysis_data, config_used, processing_time_seconds, overall_score,
                benchmark_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            final_scores = evaluation_result.get('final_scores', {})
            
            eval_params = (
                evaluation_id,
                evaluation_result.get('timestamp'),
                evaluation_result.get('question'),
                evaluation_result.get('ai_answer'),
                evaluation_result.get('golden_standard', {}).get('id'),
                json.dumps(evaluation_result.get('golden_standard', {})),
                json.dumps(evaluation_result.get('context', {})),
                json.dumps(final_scores),
                json.dumps(evaluation_result.get('consensus_scores', {})),
                json.dumps(evaluation_result.get('analysis', {})),
                json.dumps(evaluation_result.get('config_used', {})),
                evaluation_result.get('processing_time_seconds', 0.0),
                final_scores.get('overall_score', 0.0),
                final_scores.get('benchmark_category', 'unknown')
            )
            
            with self.connection:
                self.connection.execute(eval_sql, eval_params)
            
            # Store individual judge results
            judge_results = evaluation_result.get('judge_results', [])
            await self._store_judge_results(evaluation_id, judge_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store evaluation {evaluation_id}: {e}")
            return False
    
    async def _store_judge_results(self, evaluation_id: str, judge_results: List[Dict[str, Any]]):
        """Store individual judge results"""
        
        judge_sql = """
        INSERT OR REPLACE INTO judge_results (
            judge_result_id, evaluation_id, judge_model, judge_timestamp,
            individual_scores, feedback_data, confidence_scores, overall_confidence,
            compliance_score, raw_response, processing_time_seconds, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for judge_result in judge_results:
            judge_result_id = f"{evaluation_id}_{judge_result.get('judge_model', 'unknown')}"
            
            judge_params = (
                judge_result_id,
                evaluation_id,
                judge_result.get('judge_model'),
                judge_result.get('timestamp'),
                json.dumps(judge_result.get('scores', {})),
                json.dumps(judge_result.get('feedback', {})),
                json.dumps(judge_result.get('confidence', {})),
                judge_result.get('overall_confidence', 0.0),
                judge_result.get('compliance_score'),
                judge_result.get('raw_response'),
                judge_result.get('processing_time_seconds', 0.0),
                judge_result.get('error')
            )
            
            with self.connection:
                self.connection.execute(judge_sql, judge_params)
    
    async def get_evaluation_statistics(self, 
                                      time_range: Optional[Tuple[datetime, datetime]] = None,
                                      filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get comprehensive evaluation statistics"""
        
        try:
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if time_range:
                where_clauses.append("timestamp >= ? AND timestamp <= ?")
                params.extend([time_range[0].isoformat(), time_range[1].isoformat()])
            
            if filters:
                if filters.get('benchmark_category'):
                    where_clauses.append("benchmark_category = ?")
                    params.append(filters['benchmark_category'])
                
                if filters.get('min_score'):
                    where_clauses.append("overall_score >= ?")
                    params.append(filters['min_score'])
            
            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # Overall statistics
            stats = {}
            
            # Basic counts and averages
            cursor = self.connection.execute(f"""
                SELECT 
                    COUNT(*) as total_evaluations,
                    AVG(overall_score) as avg_score,
                    MIN(overall_score) as min_score,
                    MAX(overall_score) as max_score,
                    AVG(processing_time_seconds) as avg_processing_time
                FROM evaluations{where_sql}
            """, params)
            
            basic_stats = dict(cursor.fetchone())
            stats['basic_stats'] = basic_stats
            
            # Score distribution by benchmark category
            cursor = self.connection.execute(f"""
                SELECT 
                    benchmark_category,
                    COUNT(*) as count,
                    AVG(overall_score) as avg_score
                FROM evaluations{where_sql}
                GROUP BY benchmark_category
                ORDER BY avg_score DESC
            """, params)
            
            stats['score_by_category'] = [dict(row) for row in cursor.fetchall()]
            
            # Judge performance comparison
            judge_params = params.copy() if where_clauses else []
            judge_where = where_sql.replace('evaluations', 'e') if where_sql else ""
            
            cursor = self.connection.execute(f"""
                SELECT 
                    jr.judge_model,
                    COUNT(*) as evaluation_count,
                    AVG(e.overall_score) as avg_score,
                    AVG(jr.overall_confidence) as avg_confidence,
                    AVG(jr.processing_time_seconds) as avg_processing_time
                FROM judge_results jr
                JOIN evaluations e ON jr.evaluation_id = e.evaluation_id
                {judge_where}
                GROUP BY jr.judge_model
                ORDER BY avg_score DESC
            """, judge_params)
            
            stats['judge_performance'] = [dict(row) for row in cursor.fetchall()]
            
            # Temporal trends (last 30 days)
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            cursor = self.connection.execute(f"""
                SELECT 
                    DATE(timestamp) as evaluation_date,
                    COUNT(*) as daily_count,
                    AVG(overall_score) as daily_avg_score
                FROM evaluations
                WHERE timestamp >= ?{' AND ' + ' AND '.join(where_clauses) if where_clauses else ''}
                GROUP BY DATE(timestamp)
                ORDER BY evaluation_date
            """, [thirty_days_ago] + params)
            
            stats['temporal_trends'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get evaluation statistics: {e}")
            return {'error': str(e)}
    
    async def get_judge_performance_analysis(self, 
                                           judge_model: Optional[str] = None,
                                           time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """Get detailed judge performance analysis"""
        
        try:
            where_clauses = []
            params = []
            
            if judge_model:
                where_clauses.append("jr.judge_model = ?")
                params.append(judge_model)
            
            if time_range:
                where_clauses.append("e.timestamp >= ? AND e.timestamp <= ?")
                params.extend([time_range[0].isoformat(), time_range[1].isoformat()])
            
            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # Judge agreement analysis
            cursor = self.connection.execute(f"""
                SELECT 
                    jr.judge_model,
                    AVG(ABS(e.overall_score - 
                        CAST(JSON_EXTRACT(jr.individual_scores, '$.overall') AS REAL))) as avg_deviation,
                    COUNT(*) as evaluation_count
                FROM judge_results jr
                JOIN evaluations e ON jr.evaluation_id = e.evaluation_id
                {where_sql}
                GROUP BY jr.judge_model
                ORDER BY avg_deviation
            """, params)
            
            agreement_analysis = [dict(row) for row in cursor.fetchall()]
            
            # Confidence calibration
            cursor = self.connection.execute(f"""
                SELECT 
                    jr.judge_model,
                    AVG(jr.overall_confidence) as avg_confidence,
                    AVG(e.overall_score) as avg_actual_score,
                    AVG(ABS(jr.overall_confidence - e.overall_score)) as calibration_error
                FROM judge_results jr
                JOIN evaluations e ON jr.evaluation_id = e.evaluation_id
                {where_sql}
                GROUP BY jr.judge_model
            """, params)
            
            confidence_calibration = [dict(row) for row in cursor.fetchall()]
            
            return {
                'agreement_analysis': agreement_analysis,
                'confidence_calibration': confidence_calibration
            }
            
        except Exception as e:
            logger.error(f"Failed to get judge performance analysis: {e}")
            return {'error': str(e)}
    
    async def export_benchmark_report(self, 
                                    output_file: str,
                                    time_range: Optional[Tuple[datetime, datetime]] = None,
                                    include_details: bool = True) -> bool:
        """Export comprehensive benchmark report"""
        
        try:
            # Get comprehensive statistics
            stats = await self.get_evaluation_statistics(time_range)
            judge_analysis = await self.get_judge_performance_analysis(time_range=time_range)
            
            # Compile report data
            report_data = {
                'report_generated_at': datetime.now(timezone.utc).isoformat(),
                'time_range': {
                    'start': time_range[0].isoformat() if time_range else None,
                    'end': time_range[1].isoformat() if time_range else None
                },
                'statistics': stats,
                'judge_analysis': judge_analysis
            }
            
            # Include detailed evaluation data if requested
            if include_details:
                where_clauses = []
                params = []
                
                if time_range:
                    where_clauses.append("timestamp >= ? AND timestamp <= ?")
                    params.extend([time_range[0].isoformat(), time_range[1].isoformat()])
                
                where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                cursor = self.connection.execute(f"""
                    SELECT * FROM evaluations{where_sql}
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, params)
                
                detailed_evaluations = []
                for row in cursor.fetchall():
                    eval_dict = dict(row)
                    # Parse JSON fields
                    for json_field in ['golden_standard_data', 'context_data', 'final_scores', 
                                     'consensus_scores', 'analysis_data', 'config_used']:
                        if eval_dict.get(json_field):
                            try:
                                eval_dict[json_field] = json.loads(eval_dict[json_field])
                            except json.JSONDecodeError:
                                pass
                    detailed_evaluations.append(eval_dict)
                
                report_data['detailed_evaluations'] = detailed_evaluations
            
            # Write report to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Benchmark report exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export benchmark report: {e}")
            return False
    
    async def search_evaluations(self, 
                                query: str, 
                                limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search of evaluation questions and answers"""
        
        try:
            sql = """
            SELECT e.*, rank
            FROM evaluations_fts 
            JOIN evaluations e ON evaluations_fts.evaluation_id = e.evaluation_id
            WHERE evaluations_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """
            
            cursor = self.connection.execute(sql, (query, limit))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                eval_dict = dict(row)
                # Parse JSON fields
                for json_field in ['golden_standard_data', 'context_data', 'final_scores', 
                                 'consensus_scores', 'analysis_data']:
                    if eval_dict.get(json_field):
                        try:
                            eval_dict[json_field] = json.loads(eval_dict[json_field])
                        except json.JSONDecodeError:
                            pass
                results.append(eval_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Evaluation search failed: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 90) -> int:
        """Clean up old evaluation data"""
        
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
            
            # Count records to be deleted
            cursor = self.connection.execute("""
                SELECT COUNT(*) FROM evaluations WHERE timestamp < ?
            """, (cutoff_date,))
            
            records_to_delete = cursor.fetchone()[0]
            
            if records_to_delete > 0:
                # Delete old evaluations (cascades to judge_results)
                cursor = self.connection.execute("""
                    DELETE FROM evaluations WHERE timestamp < ?
                """, (cutoff_date,))
                
                # Delete old system metrics
                cursor = self.connection.execute("""
                    DELETE FROM system_metrics WHERE metric_timestamp < ?
                """, (cutoff_date,))
                
                self.connection.commit()
                
                logger.info(f"Cleaned up {records_to_delete} old evaluation records")
            
            return records_to_delete
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection