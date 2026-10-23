import os

import pytest

from vision.models import ROOT, load_patchcore


def test_refuses_to_unpickle_a_model_outside_models_dir(tmp_path):
    rogue = tmp_path / "model.pt"
    rogue.write_bytes(b"not a model")
    with pytest.raises(ValueError, match="outside"):
        load_patchcore(rogue)
    assert "TRUST_REMOTE_CODE" not in os.environ


def test_missing_model_explains_how_to_train_it():
    with pytest.raises(FileNotFoundError, match="vision.train_patchcore"):
        load_patchcore(ROOT / "models" / "does-not-exist" / "model.pt")
    assert "TRUST_REMOTE_CODE" not in os.environ
