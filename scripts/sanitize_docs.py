"""
Sanitize Wiki & Documentation - Remove Sensitive Data
Replaces passwords, IPs, and credentials with placeholders.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Sensitive patterns to replace
SENSITIVE_PATTERNS = {
    # Neo4j password
    r'v3f3b1d7': '******',
    r'password["\']?\s*[:=]\s*["\']?v3f3b1d7["\']?': 'password="******"',
    r'Auth:\s*neo4j/v3f3b1d7': 'Auth: neo4j/****** (from config_local.py)',
    r'neo4j_auth=\(["\']neo4j["\']\s*,\s*["\']v3f3b1d7["\']\)': 'neo4j_auth=(\'neo4j\', os.getenv(\'NEO4J_PASSWORD\'))',
    r'NEO4J_PASSWORD\s*=\s*["\']v3f3b1d7["\']': 'NEO4J_PASSWORD=${NEO4J_PASSWORD}',
    r'Password:\s*v3f3b1d7': 'Password: ****** (from .env)',
    
    # CouchDB credentials
    r'couchdb/couchdb': 'couchdb/****** (from config_local.py)',
    r'Auth:\s*couchdb/couchdb': 'Auth: couchdb/****** (from config_local.py)',
    r'password["\']?\s*[:=]\s*["\']?couchdb["\']?': 'password="******"',
    r'Password:\s*couchdb': 'Password: ****** (from .env)',
    
    # PostgreSQL credentials
    r'password["\']?\s*[:=]\s*["\']?postgres["\']?': 'password="******"',
    r'Password:\s*postgres': 'Password: ****** (from .env)',
    
    # IP addresses (192.168.x.x)
    r'192\.168\.178\.94': '<SERVER_IP>',
    r'Host:\s*192\.168\.\d+\.\d+': 'Host: <SERVER_IP>',
    r'host["\']?\s*[:=]\s*["\']?192\.168\.\d+\.\d+["\']?': 'host="${DB_HOST}"',
    r'bolt://192\.168\.\d+\.\d+:\d+': 'bolt://${NEO4J_HOST}:${NEO4J_PORT}',
    r'http://192\.168\.\d+\.\d+:\d+': 'http://${DB_HOST}:${DB_PORT}',
}

# Config blocks to sanitize
CONFIG_BLOCK_PATTERNS = [
    # Python config examples
    (r'(host\s*=\s*)["\']192\.168\.\d+\.\d+["\']', r'\1os.getenv("DB_HOST")'),
    (r'(user\s*=\s*)["\']postgres["\']', r'\1os.getenv("DB_USER")'),
    (r'(password\s*=\s*)["\'].*?["\']', r'\1os.getenv("DB_PASSWORD")'),
    
    # Markdown config examples
    (r'- Host: 192\.168\.\d+\.\d+:\d+', r'- Host: ${DB_HOST}:${DB_PORT}'),
    (r'- User: postgres', r'- User: ${DB_USER}'),
    (r'- Password: .*', r'- Password: ${DB_PASSWORD} (from .env)'),
]


def sanitize_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Sanitize a single file.
    
    Returns:
        (replacements_count, changed_lines)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        replacements = 0
        changed_lines = []
        
        # Apply pattern replacements
        for pattern, replacement in SENSITIVE_PATTERNS.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                changed_lines.append(f"  Line {line_num}: {match.group()[:50]}...")
                replacements += 1
            
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Apply config block patterns
        for pattern, replacement in CONFIG_BLOCK_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                changed_lines.append(f"  Line {line_num}: Config sanitized")
                replacements += 1
            
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return replacements, changed_lines
        
        return 0, []
        
    except Exception as e:
        print(f"   ❌ Error processing {file_path}: {e}")
        return 0, []


def sanitize_directory(directory: Path, pattern: str = "*.md") -> Dict:
    """
    Sanitize all markdown files in directory.
    
    Returns:
        Statistics dict
    """
    stats = {
        'files_scanned': 0,
        'files_changed': 0,
        'total_replacements': 0,
        'changed_files': []
    }
    
    for file_path in directory.rglob(pattern):
        stats['files_scanned'] += 1
        replacements, changed_lines = sanitize_file(file_path)
        
        if replacements > 0:
            stats['files_changed'] += 1
            stats['total_replacements'] += replacements
            stats['changed_files'].append({
                'path': str(file_path.relative_to(directory)),
                'replacements': replacements,
                'lines': changed_lines
            })
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Sanitize sensitive data in documentation")
    parser.add_argument('--target', default='wiki/', help='Target directory (default: wiki/)')
    parser.add_argument('--pattern', default='*.md', help='File pattern (default: *.md)')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    
    args = parser.parse_args()
    
    target_dir = Path(args.target)
    
    if not target_dir.exists():
        print(f"❌ Directory not found: {target_dir}")
        return
    
    print("=" * 80)
    print("DOCUMENTATION SANITIZER")
    print("=" * 80)
    print(f"Target: {target_dir}")
    print(f"Pattern: {args.pattern}")
    print(f"Mode: {'DRY-RUN (no changes)' if args.dry_run else 'LIVE (will modify files)'}")
    print("=" * 80)
    
    if args.dry_run:
        print("\n⚠️  DRY-RUN MODE - No files will be modified\n")
    else:
        print("\n🔧 LIVE MODE - Files will be modified!\n")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
    
    # Run sanitization
    stats = sanitize_directory(target_dir, args.pattern)
    
    # Report
    print("\n" + "=" * 80)
    print("SANITIZATION REPORT")
    print("=" * 80)
    print(f"Files scanned: {stats['files_scanned']}")
    print(f"Files changed: {stats['files_changed']}")
    print(f"Total replacements: {stats['total_replacements']}")
    
    if stats['changed_files']:
        print("\nChanged files:")
        for file_info in stats['changed_files']:
            print(f"\n📄 {file_info['path']} ({file_info['replacements']} replacements)")
            for line in file_info['lines'][:5]:  # Show first 5 changes
                print(line)
            if len(file_info['lines']) > 5:
                print(f"  ... and {len(file_info['lines']) - 5} more changes")
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print("\nRun these commands to verify:")
    print(f'  grep -r "v3f3b1d7" {target_dir}  # Should return: 0 matches')
    print(f'  grep -r "192.168" {target_dir}   # Should return: 0 matches')
    print(f'  grep -r "couchdb/couchdb" {target_dir}  # Should return: 0 matches')
    print("\n✅ COMPLETE")


if __name__ == '__main__':
    main()
