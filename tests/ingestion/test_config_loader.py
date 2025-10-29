import os
import tempfile
import textwrap
import pytest

yaml = pytest.importorskip("yaml")

from config.loader import load_ingestion_config


def test_load_ingestion_config_env_interpolation(tmp_path):
    content = textwrap.dedent(
        """
        backends:
          relational:
            enabled: ${RELATIONAL_ENABLED:false}
        feature_flags:
          ingest_new_router: ${INGEST_NEW_ROUTER:true}
        """
    )
    p = tmp_path / "ingestion.yaml"
    p.write_text(content, encoding="utf-8")

    os.environ["RELATIONAL_ENABLED"] = "true"
    os.environ.pop("INGEST_NEW_ROUTER", None)  # nutzt default:true

    cfg = load_ingestion_config(str(p))
    assert cfg["backends"]["relational"]["enabled"] is True
    assert cfg["feature_flags"]["ingest_new_router"] is True


def test_load_ingestion_config_bool_coercion(tmp_path):
    content = "fail_fast: 'False'\n"
    p = tmp_path / "ingestion.yaml"
    p.write_text(content, encoding="utf-8")

    cfg = load_ingestion_config(str(p))
    assert cfg["fail_fast"] is False
