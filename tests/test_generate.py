from clinical_pipeline.generate import generate_data


def test_generation_is_deterministic(tmp_path):
    a = generate_data(tmp_path / "a", seed=123)
    b = generate_data(tmp_path / "b", seed=123)
    assert a["patients"].equals(b["patients"])
    assert len(a["patients"]) == 240


def test_source_files_written(tmp_path):
    generate_data(tmp_path, seed=42)
    assert all((tmp_path / f"{name}.csv").exists()
               for name in ("patients", "trials", "visits", "lab_results"))
