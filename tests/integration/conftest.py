from pathlib import Path

import pytest

from tests.fixtures.lab import LabShell, build_lab_shell


@pytest.fixture
def lab_shell(tmp_path: Path) -> LabShell:
    return build_lab_shell(tmp_path)
