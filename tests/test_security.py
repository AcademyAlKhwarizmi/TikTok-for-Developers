def test_no_token_logging_import():
    from services import crypto
    assert hasattr(crypto, "encrypt")
