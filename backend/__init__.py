"""
Covina Backend Package
=====================

Microservices Backend Package for Covina Document Management System.

Contains:
- main.py: Main Backend (Port 45678) - Queries, DSGVO, Review
- ingestion.py: Ingestion Backend (Port 45679) - Upload, UDS3

Author: Covina System
Date: 25. Oktober 2025
"""

__version__ = "3.5.0"
__all__ = ["main", "ingestion"]