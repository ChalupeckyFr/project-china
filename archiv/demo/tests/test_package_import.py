from pathlib import Path

import project_china


def test_project_package_imports_from_source_tree() -> None:
    package_path = Path(project_china.__file__).resolve()
    expected_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "project_china"
        / "__init__.py"
    )

    assert package_path == expected_path.resolve()
