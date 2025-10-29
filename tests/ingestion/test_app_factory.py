from fastapi import FastAPI


def test_get_app_returns_fastapi_app():
    from ingestion.launchers.app_factory import get_app
    app = get_app()
    assert isinstance(app, FastAPI)
