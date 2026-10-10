from inspect import cleandoc
from pathlib import Path

import pytest

from scripts.makefile.self_return import find_violations, main


@pytest.mark.parametrize(
    ("body", "annotation", "should_fail"),
    [
        ("return self", '"Builder"', True),
        ("return self", "Self", False),
        ("return Builder()", '"Builder"', False),
        ("return self", '"Self"', True),
    ],
)
def test_self_contract(body: str, annotation: str, *, should_fail: bool) -> None:
    source = cleandoc(
        f"""
        class Builder:
            def configure(self) -> {annotation}:
                {body}
        """,
    )

    assert bool(list(find_violations(source))) is should_fail


def test_cli_fails_on_invalid_factory_and_accepts_self(tmp_path: Path) -> None:
    module = tmp_path / "builder.py"
    source = cleandoc(
        """
        class Builder:
            @classmethod
            def create(cls) -> "Builder":
                return cls()
        """,
    )
    module.write_text(source)

    assert main((str(tmp_path),)) == 1

    module.write_text(source.replace('"Builder"', "Self"))
    assert main((str(tmp_path),)) == 0
