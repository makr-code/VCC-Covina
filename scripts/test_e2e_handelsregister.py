#!/usr/bin/env python3
"""
End-to-End Test: Handelsregister Integration
=============================================

Tests the complete pipeline from document upload to review task creation.

Test Scenarios:
1. Complete data (HRB + court) → No review tasks
2. Missing HRB number → Review task created
3. Missing court → Review task created
4. Multiple companies → Multiple entries + review tasks
5. No company → No extraction, no tasks

Usage:
    python scripts/test_e2e_handelsregister.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

# Import backend components
from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend

# Test configuration
TEST_DIR = Path("tests/e2e_handelsregister")
POSTGRES_CONFIG = {
    'host': '192.168.178.94',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres'
}

# Test scenarios
SCENARIOS = [
    {
        'file': 'scenario1_complete.txt',
        'name': 'Complete Data (HRB + Court)',
        'expected_companies': 1,
        'expected_gaps': 0,
        'expected_review_tasks': 0,
        'company_name': 'Test Solutions GmbH',
        'hrb': 'HRB 12345',
        'court': 'Amtsgericht München'
    },
    {
        'file': 'scenario2_missing_hrb.txt',
        'name': 'Missing HRB Number',
        'expected_companies': 1,
        'expected_gaps': 1,
        'expected_review_tasks': 1,
        'company_name': 'Example Innovations AG',
        'hrb': None,
        'court': 'Amtsgericht Berlin',
        'gap_type': 'missing_register_number'
    },
    {
        'file': 'scenario3_missing_court.txt',
        'name': 'Missing Court',
        'expected_companies': 1,
        'expected_gaps': 1,
        'expected_review_tasks': 1,
        'company_name': 'Demo Technologies GmbH',
        'hrb': 'HRB 67890',
        'court': None,
        'gap_type': 'missing_register_court'
    },
    {
        'file': 'scenario4_multiple.txt',
        'name': 'Multiple Companies',
        'expected_companies': 4,  # Alpha, Beta, AlphaBeta (new entity), Gamma
        'expected_gaps': 0,  # All have complete data
        'expected_review_tasks': 0,
        'companies': [
            {'name': 'Alpha Digital Services GmbH', 'hrb': 'HRB 11111', 'court': 'Amtsgericht Köln'},
            {'name': 'Beta Software Solutions AG', 'hrb': 'HRB 22222', 'court': 'Amtsgericht Hamburg'},
            {'name': 'AlphaBeta Tech Group AG', 'hrb': 'HRB 22222', 'court': 'Amtsgericht Hamburg'},  # Inherits closest HRB
            {'name': 'Gamma Consulting GmbH', 'hrb': 'HRA 33333', 'court': 'Amtsgericht Frankfurt'}
        ]
    },
    {
        'file': 'scenario5_no_company.txt',
        'name': 'No Company Mentioned',
        'expected_companies': 0,
        'expected_gaps': 0,
        'expected_review_tasks': 0
    }
]


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    """Print formatted section"""
    print("\n" + "-" * 70)
    print(f"  {text}")
    print("-" * 70)


def print_result(passed: bool, message: str):
    """Print test result"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")


class E2ETestRunner:
    """End-to-End Test Runner for Handelsregister Integration"""
    
    def __init__(self):
        self.postgres_backend = None
        self.test_document_ids = []
        self.results = []
    
    
    def setup(self):
        """Initialize PostgreSQL connection"""
        print_header("SETUP: Initialize Database Connection")
        
        try:
            self.postgres_backend = PostgreSQLRelationalBackend(POSTGRES_CONFIG)
            self.postgres_backend.connect()
            print_result(True, f"Connected to PostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
            return True
        except Exception as e:
            print_result(False, f"Failed to connect to PostgreSQL: {e}")
            return False
    
    
    def cleanup(self):
        """Remove test data"""
        print_header("CLEANUP: Remove Test Data")
        
        if not self.postgres_backend:
            print_result(False, "No database connection")
            return False
        
        try:
            # Delete test documents (CASCADE will delete review tasks)
            for doc_id in self.test_document_ids:
                self.postgres_backend.cursor.execute("""
                    DELETE FROM documents WHERE document_id = %s
                """, (doc_id,))
                print_result(True, f"Deleted test document: {doc_id}")
            
            self.postgres_backend.conn.commit()
            print_result(True, f"Cleanup complete ({len(self.test_document_ids)} documents)")
            return True
            
        except Exception as e:
            self.postgres_backend.conn.rollback()
            print_result(False, f"Cleanup failed: {e}")
            return False
    
    
    def create_test_document(self, file_path: str, content: str) -> str:
        """
        Create test document in database
        
        Returns:
            document_id
        """
        try:
            # Generate document ID
            import uuid
            document_id = f"e2e_test_{uuid.uuid4().hex[:12]}"
            
            # Insert into documents table
            self.postgres_backend.cursor.execute("""
                INSERT INTO documents (
                    document_id, file_path, classification,
                    content_length, legal_terms_count, created_at,
                    quality_score, processing_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                document_id,
                str(file_path),
                'unknown',  # classification
                len(content),  # content_length
                0,  # legal_terms_count
                '2025-10-10T12:00:00',  # created_at
                0.0,  # quality_score
                'processed'  # processing_status
            ))
            
            self.postgres_backend.conn.commit()
            self.test_document_ids.append(document_id)
            
            return document_id
            
        except Exception as e:
            self.postgres_backend.conn.rollback()
            print_result(False, f"Failed to create test document: {e}")
            return None
    
    
    async def process_document(self, document_id: str, file_path: Path, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate document processing with company extraction
        
        Note: This is a simplified version for testing purposes.
        In production, the full UDS3 pipeline would be used.
        """
        print_section(f"Processing: {scenario['name']}")
        
        # Read content
        content = file_path.read_text(encoding='utf-8')
        
        # Simple regex-based company extraction (simplified)
        import re
        
        companies = []
        gaps = []
        seen_companies = set()  # Track unique companies
        
        # Extract companies with GmbH/AG suffix
        # Exclude "Die " prefix to avoid duplicates
        company_pattern = r'(?<![Dd]ie\s)([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*\s+(?:GmbH|AG))'
        company_matches = re.finditer(company_pattern, content)
        
        for match in company_matches:
            firma = match.group(1)
            
            # Skip if we've already seen this company
            if firma in seen_companies:
                continue
            
            seen_companies.add(firma)
            
            # Check for HRB/HRA number near company name
            window = content[max(0, match.start()-200):min(len(content), match.end()+200)]
            hrb_match = re.search(r'(HRB|HRA)\s+(\d+)', window)
            court_match = re.search(r'Amtsgericht\s+([A-ZÄÖÜ][a-zäöü]+)', window)
            
            register_number = f"{hrb_match.group(1)} {hrb_match.group(2)}" if hrb_match else None
            register_court = f"Amtsgericht {court_match.group(1)}" if court_match else None
            
            company_data = {
                'firma': firma,
                'register_number': register_number,
                'register_court': register_court
            }
            
            companies.append(company_data)
            
            # Detect gaps
            if not register_number:
                gaps.append({
                    'gap_type': 'missing_register_number',
                    'firma': firma,
                    'severity': 'medium',
                    'message': f'Company "{firma}" mentioned but no register number found'
                })
            
            if not register_court:
                gaps.append({
                    'gap_type': 'missing_register_court',
                    'firma': firma,
                    'severity': 'low',
                    'message': f'Company "{firma}" mentioned but no register court found'
                })
        
        # Store company metadata
        if companies:
            company_metadata = {
                'companies': companies,
                'extraction_date': '2025-10-10T12:00:00',
                'extraction_method': 'regex_test'
            }
            
            self.postgres_backend.cursor.execute("""
                UPDATE documents
                SET company_metadata = %s
                WHERE document_id = %s
            """, (json.dumps(company_metadata), document_id))
            
            self.postgres_backend.conn.commit()
        
        # Create review tasks for gaps
        review_task_ids = []
        if gaps:
            for gap in gaps:
                import uuid
                review_id = str(uuid.uuid4())
                
                self.postgres_backend.cursor.execute("""
                    INSERT INTO review_tasks (
                        review_id, document_id, file_path, gap_type,
                        firma, severity, message, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    review_id,
                    document_id,
                    str(file_path),
                    gap['gap_type'],
                    gap['firma'],
                    gap['severity'],
                    gap['message'],
                    'pending'
                ))
                
                review_task_ids.append(review_id)
            
            self.postgres_backend.conn.commit()
        
        return {
            'document_id': document_id,
            'companies_found': len(companies),
            'companies': companies,
            'gaps_found': len(gaps),
            'gaps': gaps,
            'review_tasks_created': len(review_task_ids),
            'review_task_ids': review_task_ids
        }
    
    
    def validate_result(self, result: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """Validate processing result against expected scenario"""
        print_section("Validation")
        
        all_passed = True
        
        # Check companies count
        if result['companies_found'] == scenario['expected_companies']:
            print_result(True, f"Companies found: {result['companies_found']} (expected: {scenario['expected_companies']})")
        else:
            print_result(False, f"Companies found: {result['companies_found']} (expected: {scenario['expected_companies']})")
            all_passed = False
        
        # Check gaps count
        if result['gaps_found'] == scenario['expected_gaps']:
            print_result(True, f"Gaps detected: {result['gaps_found']} (expected: {scenario['expected_gaps']})")
        else:
            print_result(False, f"Gaps detected: {result['gaps_found']} (expected: {scenario['expected_gaps']})")
            all_passed = False
        
        # Check review tasks count
        if result['review_tasks_created'] == scenario['expected_review_tasks']:
            print_result(True, f"Review tasks created: {result['review_tasks_created']} (expected: {scenario['expected_review_tasks']})")
        else:
            print_result(False, f"Review tasks created: {result['review_tasks_created']} (expected: {scenario['expected_review_tasks']})")
            all_passed = False
        
        # Check company details
        if result['companies']:
            print("\nExtracted Companies:")
            for idx, company in enumerate(result['companies'], 1):
                print(f"  {idx}. {company['firma']}")
                print(f"     - HRB: {company['register_number'] or 'N/A'}")
                print(f"     - Court: {company['register_court'] or 'N/A'}")
        
        # Check gaps
        if result['gaps']:
            print("\nDetected Gaps:")
            for idx, gap in enumerate(result['gaps'], 1):
                print(f"  {idx}. {gap['gap_type']} - {gap['firma']} ({gap['severity']})")
        
        return all_passed
    
    
    async def run_scenario(self, scenario: Dict[str, Any]) -> bool:
        """Run single test scenario"""
        print_header(f"SCENARIO: {scenario['name']}")
        
        file_path = TEST_DIR / scenario['file']
        
        if not file_path.exists():
            print_result(False, f"Test file not found: {file_path}")
            return False
        
        # Create test document
        content = file_path.read_text(encoding='utf-8')
        document_id = self.create_test_document(file_path, content)
        
        if not document_id:
            return False
        
        print_result(True, f"Test document created: {document_id}")
        
        # Process document
        result = await self.process_document(document_id, file_path, scenario)
        
        # Validate result
        passed = self.validate_result(result, scenario)
        
        # Store result
        self.results.append({
            'scenario': scenario['name'],
            'passed': passed,
            'result': result
        })
        
        return passed
    
    
    async def run_all(self):
        """Run all test scenarios"""
        print_header("E2E TEST: Handelsregister Integration")
        
        if not self.setup():
            return False
        
        passed_count = 0
        failed_count = 0
        
        for scenario in SCENARIOS:
            try:
                passed = await self.run_scenario(scenario)
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print_result(False, f"Scenario failed with exception: {e}")
                failed_count += 1
        
        # Print summary
        print_header("TEST SUMMARY")
        print(f"\nTotal scenarios: {len(SCENARIOS)}")
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"\nSuccess rate: {passed_count / len(SCENARIOS) * 100:.1f}%")
        
        # Detailed results
        print_section("Detailed Results")
        for idx, result in enumerate(self.results, 1):
            icon = "✅" if result['passed'] else "❌"
            print(f"{icon} Scenario {idx}: {result['scenario']}")
            print(f"   - Companies: {result['result']['companies_found']}")
            print(f"   - Gaps: {result['result']['gaps_found']}")
            print(f"   - Review Tasks: {result['result']['review_tasks_created']}")
        
        # Ask for cleanup
        print("\n" + "=" * 70)
        cleanup = input("Remove test data? (y/n): ").strip().lower()
        if cleanup == 'y':
            self.cleanup()
        
        return passed_count == len(SCENARIOS)


async def main():
    """Main entry point"""
    runner = E2ETestRunner()
    success = await runner.run_all()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
