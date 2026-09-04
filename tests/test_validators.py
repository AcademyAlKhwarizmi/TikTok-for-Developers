from utils.validators import normalize_hashtags
def test_hashtags():
    assert normalize_hashtags("fyp #egypt") == "#fyp #egypt"
