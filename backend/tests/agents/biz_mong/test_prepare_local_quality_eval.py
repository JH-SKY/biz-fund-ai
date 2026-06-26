from src.app.scripts.prepare_local_quality_eval import _parse_args


def test_parse_args_uses_default_prepare_options(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepare_local_quality_eval.py"])

    args = _parse_args()

    assert args.database_url is None
    assert args.skip_freeze is False
    assert args.skip_embedding is False
    assert args.run_eval is False
    assert args.eval_limit is None


def test_parse_args_reads_skip_flags_and_database_url(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare_local_quality_eval.py",
            "--database-url",
            "postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai",
            "--skip-freeze",
            "--skip-embedding",
            "--run-eval",
            "--eval-limit",
            "5",
        ],
    )

    args = _parse_args()

    assert args.database_url == "postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai"
    assert args.skip_freeze is True
    assert args.skip_embedding is True
    assert args.run_eval is True
    assert args.eval_limit == 5
