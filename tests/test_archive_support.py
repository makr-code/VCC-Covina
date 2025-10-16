#!/usr/bin/env python3
"""
Test-Skript für Archive-Unterstützung
Testet ZIP, TAR, 7Z Archive-Extraktion und -Verarbeitung
"""

import os
import sys
import tempfile
import zipfile
import tarfile
from pathlib import Path

try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False
    print("⚠️ py7zr nicht installiert - 7Z-Tests werden übersprungen")

try:
    import rarfile
    HAS_RAR = True
except ImportError:
    HAS_RAR = False
    print("⚠️ rarfile nicht installiert - RAR-Tests werden übersprungen")


def create_test_files(temp_dir: Path) -> list:
    """Erstelle Test-Dateien für Archive"""
    # Erstelle Verzeichnis falls nicht vorhanden
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    test_files = []
    
    # Text-Datei
    text_file = temp_dir / "test_document.txt"
    text_file.write_text("Dies ist ein Test-Dokument für die Archiv-Verarbeitung.\n" * 10, encoding='utf-8')
    test_files.append(text_file)
    
    # Markdown-Datei
    md_file = temp_dir / "readme.md"
    md_file.write_text("# Test Markdown\n\n## Beschreibung\nTest-Dokument.\n", encoding='utf-8')
    test_files.append(md_file)
    
    # JSON-Datei
    json_file = temp_dir / "data.json"
    json_file.write_text('{"name": "Test", "value": 123, "active": true}', encoding='utf-8')
    test_files.append(json_file)
    
    print(f"✅ {len(test_files)} Test-Dateien erstellt")
    return test_files


def test_zip_creation(test_files: list, output_dir: Path) -> Path:
    """Erstelle ZIP-Archiv"""
    zip_path = output_dir / "test_archive.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in test_files:
            zipf.write(file, arcname=file.name)
    
    print(f"✅ ZIP erstellt: {zip_path} ({zip_path.stat().st_size} bytes)")
    return zip_path


def test_tar_creation(test_files: list, output_dir: Path) -> list:
    """Erstelle TAR-Archive (normal, gz, bz2, xz)"""
    tar_archives = []
    
    # TAR (uncompressed)
    tar_path = output_dir / "test_archive.tar"
    with tarfile.open(tar_path, 'w') as tarf:
        for file in test_files:
            tarf.add(file, arcname=file.name)
    tar_archives.append(tar_path)
    print(f"✅ TAR erstellt: {tar_path.name} ({tar_path.stat().st_size} bytes)")
    
    # TAR.GZ
    targz_path = output_dir / "test_archive.tar.gz"
    with tarfile.open(targz_path, 'w:gz') as tarf:
        for file in test_files:
            tarf.add(file, arcname=file.name)
    tar_archives.append(targz_path)
    print(f"✅ TAR.GZ erstellt: {targz_path.name} ({targz_path.stat().st_size} bytes)")
    
    # TAR.BZ2
    tarbz2_path = output_dir / "test_archive.tar.bz2"
    with tarfile.open(tarbz2_path, 'w:bz2') as tarf:
        for file in test_files:
            tarf.add(file, arcname=file.name)
    tar_archives.append(tarbz2_path)
    print(f"✅ TAR.BZ2 erstellt: {tarbz2_path.name} ({tarbz2_path.stat().st_size} bytes)")
    
    # TAR.XZ
    tarxz_path = output_dir / "test_archive.tar.xz"
    with tarfile.open(tarxz_path, 'w:xz') as tarf:
        for file in test_files:
            tarf.add(file, arcname=file.name)
    tar_archives.append(tarxz_path)
    print(f"✅ TAR.XZ erstellt: {tarxz_path.name} ({tarxz_path.stat().st_size} bytes)")
    
    return tar_archives


def test_7z_creation(test_files: list, output_dir: Path) -> Path:
    """Erstelle 7Z-Archiv"""
    if not HAS_7Z:
        print("⚠️ py7zr nicht verfügbar - 7Z-Test übersprungen")
        return None
    
    sz_path = output_dir / "test_archive.7z"
    
    with py7zr.SevenZipFile(sz_path, 'w') as szf:
        for file in test_files:
            szf.write(file, arcname=file.name)
    
    print(f"✅ 7Z erstellt: {sz_path} ({sz_path.stat().st_size} bytes)")
    return sz_path


def test_extraction(archive_path: Path, archive_type: str) -> bool:
    """Teste Archiv-Extraktion"""
    extract_dir = Path(tempfile.mkdtemp(prefix="test_extract_"))
    
    try:
        if archive_type == "zip":
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_dir)
        
        elif archive_type.startswith("tar"):
            mode = 'r'
            if 'gz' in archive_type:
                mode = 'r:gz'
            elif 'bz2' in archive_type:
                mode = 'r:bz2'
            elif 'xz' in archive_type:
                mode = 'r:xz'
            
            with tarfile.open(archive_path, mode) as tarf:
                tarf.extractall(extract_dir)
        
        elif archive_type == "7z":
            if not HAS_7Z:
                return False
            with py7zr.SevenZipFile(archive_path, 'r') as szf:
                szf.extractall(extract_dir)
        
        # Zähle extrahierte Dateien
        extracted_files = list(extract_dir.glob("*"))
        print(f"  ✅ {len(extracted_files)} Dateien aus {archive_path.name} extrahiert")
        
        # Cleanup
        import shutil
        shutil.rmtree(extract_dir, ignore_errors=True)
        
        return len(extracted_files) > 0
        
    except Exception as e:
        print(f"  ❌ Fehler beim Extrahieren von {archive_path.name}: {e}")
        return False


def test_archive_detection():
    """Teste Archiv-Erkennung anhand Dateiendung"""
    archive_extensions = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
        '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz'
    }
    
    test_cases = [
        ("document.zip", True),
        ("archive.tar.gz", True),
        ("compressed.tgz", True),
        ("file.7z", True),
        ("data.tar.bz2", True),
        ("text.txt", False),
        ("image.jpg", False),
        ("document.pdf", False),
    ]
    
    print("\n📋 Teste Archiv-Erkennung:")
    all_passed = True
    
    for filename, should_be_archive in test_cases:
        file_ext = Path(filename).suffix.lower()
        is_archive = file_ext in archive_extensions or '.tar' in filename
        
        if is_archive == should_be_archive:
            print(f"  ✅ {filename}: {'Archiv' if is_archive else 'Kein Archiv'}")
        else:
            print(f"  ❌ {filename}: Erwartet {'Archiv' if should_be_archive else 'Kein Archiv'}, erkannt als {'Archiv' if is_archive else 'Kein Archiv'}")
            all_passed = False
    
    return all_passed


def main():
    """Haupt-Test-Funktion"""
    print("🧪 Starte Archive-Support-Tests\n")
    
    # Test 1: Archiv-Erkennung
    detection_passed = test_archive_detection()
    
    # Test 2: Archiv-Erstellung und Extraktion
    with tempfile.TemporaryDirectory(prefix="covina_archive_test_") as temp_dir:
        temp_path = Path(temp_dir)
        
        # Erstelle Test-Dateien
        print("\n📁 Erstelle Test-Dateien:")
        test_files = create_test_files(temp_path / "source")
        
        # Erstelle Output-Verzeichnis
        output_dir = temp_path / "archives"
        output_dir.mkdir()
        
        # Test ZIP
        print("\n📦 Teste ZIP-Archive:")
        zip_path = test_zip_creation(test_files, output_dir)
        zip_ok = test_extraction(zip_path, "zip")
        
        # Test TAR-Varianten
        print("\n📦 Teste TAR-Archive:")
        tar_archives = test_tar_creation(test_files, output_dir)
        tar_types = ["tar", "tar.gz", "tar.bz2", "tar.xz"]
        tar_results = []
        for archive, tar_type in zip(tar_archives, tar_types):
            result = test_extraction(archive, tar_type)
            tar_results.append(result)
        
        # Test 7Z
        print("\n📦 Teste 7Z-Archive:")
        if HAS_7Z:
            sz_path = test_7z_creation(test_files, output_dir)
            sz_ok = test_extraction(sz_path, "7z") if sz_path else False
        else:
            sz_ok = None
        
        # Zusammenfassung
        print("\n" + "="*60)
        print("📊 Test-Zusammenfassung:")
        print("="*60)
        print(f"  {'✅' if detection_passed else '❌'} Archiv-Erkennung: {'Bestanden' if detection_passed else 'Fehlgeschlagen'}")
        print(f"  {'✅' if zip_ok else '❌'} ZIP-Extraktion: {'Bestanden' if zip_ok else 'Fehlgeschlagen'}")
        print(f"  {'✅' if all(tar_results) else '❌'} TAR-Extraktion: {sum(tar_results)}/{len(tar_results)} bestanden")
        
        if sz_ok is not None:
            print(f"  {'✅' if sz_ok else '❌'} 7Z-Extraktion: {'Bestanden' if sz_ok else 'Fehlgeschlagen'}")
        else:
            print(f"  ⚠️  7Z-Extraktion: Übersprungen (py7zr nicht installiert)")
        
        # RAR-Status
        if HAS_RAR:
            print(f"  ✅ RAR-Support: Verfügbar (rarfile installiert)")
        else:
            print(f"  ⚠️  RAR-Support: Nicht verfügbar (rarfile nicht installiert)")
        
        # Gesamt-Ergebnis
        all_tests_passed = detection_passed and zip_ok and all(tar_results)
        if sz_ok is not None:
            all_tests_passed = all_tests_passed and sz_ok
        
        print("="*60)
        if all_tests_passed:
            print("🎉 Alle Tests bestanden!")
            return 0
        else:
            print("❌ Einige Tests fehlgeschlagen")
            return 1


if __name__ == "__main__":
    sys.exit(main())
