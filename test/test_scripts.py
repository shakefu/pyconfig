"""
Tests for the pyconfig scripts.

"""

from pathlib import Path
from typing import Callable, Dict, Union

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from pyconfig import scripts

# Type alias for the recursive file definition structure
FileDef = Dict[str, Union[str, "FileDef"]]
# Type alias for the factory fixture
CreateFilesFixture = Callable[[FileDef], Path]


@pytest.fixture
def create_test_files(tmp_path: Path) -> CreateFilesFixture:
    """A factory fixture to create temporary files and directories for testing.

    The created files are automatically cleaned up by pytest's tmp_path fixture.
    """

    def _create_files_recursively(base_path: Path, file_defs: FileDef) -> None:
        for name, content in file_defs.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir()
                _create_files_recursively(path, content)
            else:
                path.write_text(content)

    def _create_test_files(file_defs: FileDef) -> Path:
        """
        Create files and directories from a dictionary of definitions.

        If a single file definition is provided, it returns the path to that file.
        Otherwise, it returns the base temporary path.

        :param file_defs: A dictionary where keys are filenames and values are
                          their content. If content is a dict, a directory is
                          created and the process is repeated.
        """
        _create_files_recursively(tmp_path, file_defs)
        if len(file_defs) == 1:
            name, content = next(iter(file_defs.items()))
            if isinstance(content, str):
                return tmp_path / name
        return tmp_path

    return _create_test_files


def test_main_help(capsys: CaptureFixture) -> None:
    """Tests that the --help flag works as expected."""
    with pytest.raises(SystemExit) as e:
        scripts.main(["--help"])

    assert e.value.code == 0

    captured = capsys.readouterr()
    assert "usage: pyconfig" in captured.out
    assert "Helper for working with pyconfigs" in captured.out


def test_main_filename(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --filename flag works as expected."""
    test_file = create_test_files(
        {
            "test_config.py": """
import pyconfig

pyconfig.get('test.key.one')
pyconfig.setting('test.key.two', 'default_value')
pyconfig.set('test.key.three', True)
"""
        }
    )

    scripts.main(["--filename", str(test_file), "--color"])

    captured = capsys.readouterr()
    expected_output = (
        "test.key.one = <not set>\n"
        "test.key.three = True\n"
        "test.key.two = 'default_value' "
    )
    assert captured.out == expected_output


def test_main_only_keys(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --only-keys flag works as expected."""
    test_file = create_test_files(
        {
            "test_config.py": """
import pyconfig

pyconfig.get('test.key.one')
pyconfig.setting('test.key.two', 'default_value')
pyconfig.set('test.key.three', True)
"""
        }
    )
    scripts.main(["--filename", str(test_file), "--only-keys", "--color"])

    captured = capsys.readouterr()
    expected_output = "test.key.one\ntest.key.three\ntest.key.two "
    assert captured.out == expected_output


def test_main_module(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --module flag works as expected."""
    # Create a package structure
    tmp_path = create_test_files(
        {
            "testpkg": {
                "__init__.py": "",
                "sub": {
                    "__init__.py": "",
                    "mod.py": "import pyconfig\npyconfig.get('test.key.one')",
                },
            }
        }
    )

    # Add the temp path to sys.path so the module can be imported
    import sys

    sys.path.insert(0, str(tmp_path))

    try:
        scripts.main(["--module", "testpkg.sub.mod", "--color"])
    finally:
        # remove from path
        sys.path.pop(0)

    captured = capsys.readouterr()
    expected_output = "test.key.one = <not set> "
    assert captured.out == expected_output


def test_main_no_pygments_color_error(
    capsys: CaptureFixture,
    monkeypatch: MonkeyPatch,
    create_test_files: CreateFilesFixture,
) -> None:
    """Tests that an error is raised when --color is used without pygments."""
    test_file = create_test_files(
        {"test_config.py": "import pyconfig\npyconfig.get('k')"}
    )

    monkeypatch.setattr(scripts, "pygments", None)

    with pytest.raises(SystemExit) as e:
        # We need to force color to be on, which it is by default when pygments
        # is missing.
        scripts.main(["--filename", str(test_file), "--color"])
    assert e.value.code == 1

    captured = capsys.readouterr()
    assert "Pygments is required" in captured.err


def test_main_view_call(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --view-call flag works as expected."""
    test_file = create_test_files(
        {"test_config.py": "import pyconfig\npyconfig.get('test.key.one')"}
    )
    scripts.main(["--filename", str(test_file), "--view-call", "--color"])

    captured = capsys.readouterr()
    expected_output = "pyconfig.get('test.key.one') "
    assert captured.out == expected_output


def test_main_source(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --source flag works as expected."""
    test_file = create_test_files(
        {"test_config.py": "import pyconfig\npyconfig.get('test.key.one')"}
    )
    scripts.main(["--filename", str(test_file), "--source", "--color"])

    captured = capsys.readouterr()
    expected_output = f"# {test_file.name}, line 2\ntest.key.one = <not set> "
    assert captured.out == expected_output


def test_main_parse_dir(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that parsing a directory works as expected."""
    test_dir = create_test_files(
        {
            "config_dir": {
                "a.py": "import pyconfig\npyconfig.get('key.a')",
                "b.py": "import pyconfig\npyconfig.get('key.b')",
            }
        }
    )
    scripts.main(["--filename", str(test_dir / "config_dir"), "--color"])

    captured = capsys.readouterr()
    expected_output = "key.a = <not set>\nkey.b = <not set> "
    assert captured.out == expected_output


def test_main_load_configs(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --load-configs flag works as expected."""
    test_file = create_test_files(
        {"test_config.py": "import pyconfig\npyconfig.get('test.key.one')"}
    )
    # Set a value in the config to be loaded
    import pyconfig

    pyconfig.set("test.key.one", "loaded_value")

    scripts.main(["--filename", str(test_file), "--load-configs", "--color"])

    captured = capsys.readouterr()
    expected_output = "test.key.one = 'loaded_value' "
    assert expected_output in captured.out

    # Clean up the config
    del pyconfig.Config().settings["test.key.one"]


def test_main_natural_sort(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --natural-sort flag works as expected."""
    test_dir = create_test_files(
        {
            "b.py": "import pyconfig\npyconfig.get('key.b')",
            "a.py": "import pyconfig\npyconfig.get('key.a')",
        }
    )
    scripts.main(["--filename", str(test_dir), "--natural-sort", "--color"])

    captured = capsys.readouterr()
    # The output should be sorted by filename (a.py, then b.py)
    expected_output = "key.a = <not set>\nkey.b = <not set> "
    assert captured.out == expected_output


def test_main_all_keys(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that the --all flag works as expected."""
    test_file = create_test_files(
        {
            "test_config.py": """
import pyconfig

pyconfig.get('test.key.one')
pyconfig.setting('test.key.two', 'default_value')
pyconfig.set('test.key.one', 'default_for_one')
"""
        }
    )
    scripts.main(["--filename", str(test_file), "--all", "--color"])

    captured = capsys.readouterr()
    assert "test.key.one = <not set>" in captured.out
    assert "test.key.one = 'default_for_one'" in captured.out
    assert "test.key.two = 'default_value'" in captured.out


def test_main_syntax_error_file(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that a file with a syntax error is handled gracefully."""
    test_file = create_test_files({"bad_syntax.py": "this is not python"})
    with pytest.raises(SystemExit) as e:
        scripts.main(["--filename", str(test_file), "--color"])
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "No pyconfig calls" in captured.err


def test_main_unparseable_call(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that a call that can't be parsed is handled correctly."""
    test_file = create_test_files(
        {"unparseable.py": "import pyconfig\npyconfig.get('key', 'default')"}
    )
    scripts.main(["-f", str(test_file), "--color"])

    captured = capsys.readouterr()
    assert "key = 'default'" in captured.out


def test_main_unparseable_pyconfig_call(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that a pyconfig call with an unparseable key is handled."""
    test_file = create_test_files(
        {"unparseable.py": "import pyconfig\npyconfig.get(some_variable)"}
    )
    scripts.main(["-f", str(test_file), "--color"])
    captured = capsys.readouterr()
    assert "some_variable = <not set>" in captured.out


def test_main_module_not_found(capsys: CaptureFixture) -> None:
    """Tests that a non-existent module raises an error."""
    with pytest.raises(SystemExit) as e:
        scripts.main(["--module", "nonexistent.module"])
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Could not load module or package" in captured.err


def test_main_no_calls_found(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that a file with no pyconfig calls produces the correct message."""
    test_file = create_test_files({"no_calls.py": "print('hello')"})
    with pytest.raises(SystemExit) as e:
        scripts.main(["--filename", str(test_file)])
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "No pyconfig calls" in captured.err


def test_main_file_not_found(capsys: CaptureFixture) -> None:
    """Tests that a non-existent file path raises an error."""
    with pytest.raises(SystemExit) as e:
        scripts.main(["--filename", "nonexistent_file.py"])
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Could not determine file type" in captured.err


def test_main_unparseable_module(
    capsys: CaptureFixture, monkeypatch: MonkeyPatch
) -> None:
    """Tests that an unparseable module (e.g., no __file__) is handled."""
    monkeypatch.setattr(
        scripts, "_get_module_filename", lambda _: scripts.Unparseable()
    )
    with pytest.raises(SystemExit) as e:
        scripts.main(["--module", "some.module"])
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Could not determine module source" in captured.err


def test_main_colorized_output(
    capsys: CaptureFixture,
    create_test_files: CreateFilesFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that the output is colorized when pygments is available."""
    # This test will only work if pygments is actually installed.
    if not scripts.pygments:
        pytest.skip("pygments not installed")

    # Keep a reference to the original function
    original_create_parser = scripts._create_parser

    # Force color to be on
    monkeypatch.setattr(
        scripts,
        "_create_parser",
        lambda pygments_available: original_create_parser(True),
    )

    test_file = create_test_files({"c.py": "import pyconfig\npyconfig.get('key.c')"})
    scripts.main(["--filename", str(test_file)])

    captured = capsys.readouterr()
    # Check for the ANSI escape code for color.
    assert "\x1b[" in captured.out


def test_pyconfig_call_as_namespace() -> None:
    """Tests the as_namespace method of the _PyconfigCall class."""
    source = ("", "", 0, 0)
    call = scripts._PyconfigCall("get", "my.app.key", None, source)
    assert call.as_namespace(namespace="my.app") == "key = <not set>"
    assert call.as_namespace(namespace="other.app") == "my.app.key = <not set>"
    assert call.as_namespace() == "my.app.key = <not set>"


def test_pyconfig_call_as_namespace_unparseable() -> None:
    """Tests the as_namespace method with an unparseable key."""
    source_line = "pyconfig.get(some_variable)"
    source = ("unparseable.py", source_line, 1, 0)
    call = scripts._PyconfigCall("get", scripts.Unparseable(), [], source)
    assert call.as_namespace(namespace="my.app") == "<some_variable> = <not set>"
    assert call.as_namespace() == "<some_variable> = <not set>"


def test_main_false_and_none_defaults(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests that False and None defaults are handled correctly."""
    test_file = create_test_files(
        {
            "test_config.py": """
import pyconfig
pyconfig.setting('a', False)
pyconfig.setting('b', None)
"""
        }
    )
    scripts.main(["--filename", str(test_file), "--color"])

    captured = capsys.readouterr()
    assert "a = False" in captured.out
    assert "b = None" in captured.out


def test_main_file_with_encoding(
    capsys: CaptureFixture, create_test_files: CreateFilesFixture
) -> None:
    """Tests parsing a file with a non-UTF-8 encoding."""
    # The content is still UTF-8, but we're testing the declaration parsing.
    content = "# -*- coding: latin-1 -*-\nimport pyconfig\npyconfig.get('key.d')"
    test_file = create_test_files({"encoded.py": content})
    scripts.main(["--filename", str(test_file), "--color"])
    captured = capsys.readouterr()
    assert "key.d = <not set>" in captured.out
