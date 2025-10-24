

# ================================================================
# MAIN ENTRY POINT
# ================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Covina Main Backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=45678, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Log level")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Covina Main Backend")
    logger.info("=" * 60)
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Log-Level: {args.log_level.upper()}")
    logger.info(f"  Neo4j: {os.getenv('NEO4J_URI', 'neo4j://192.168.178.94:7687')}")
    logger.info(f"  ChromaDB: {os.getenv('CHROMA_HOST', 'http://192.168.178.94:8000')}")
    logger.info("=" * 60)
    
    # Start uvicorn server
    uvicorn.run(
        "backend:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )
