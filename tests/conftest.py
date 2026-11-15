import pytest

from clinical_pipeline.generate import generate_data


@pytest.fixture
def source_dir(tmp_path):
    path = tmp_path / "source"
    generate_data(path, seed=7)
    return path
