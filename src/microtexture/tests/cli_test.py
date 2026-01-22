import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from importlib.resources import files


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def dummy_template():
    template_path = files("microtexture") / "tests/dummy_template.j2"
    assert template_path.is_file()
    return str(template_path)


@pytest.fixture
def dummy_config_yaml():
    template_path = files("microtexture") / "tests/dummy_inputs.yaml"
    assert template_path.is_file()
    return str(template_path)


@pytest.fixture
def dummy_input_file(temp_dir):
    input_file = os.path.join(temp_dir, "test.ctf")
    Path(input_file).touch()
    return input_file


def test_parse_default_config_yaml(dummy_input_file):
    """Check that the defaults.yaml works as --config file"""

    from microtexture.cli import parse_args

    defaults_yaml = str(files("microtexture") / "defaults.yaml")

    with patch("sys.argv", ["cli.py", dummy_input_file, "--config", defaults_yaml, "--no-runner"]):
        parse_args()


def test_parse_test_config_yaml(dummy_config_yaml, dummy_input_file):

    from microtexture.cli import parse_args

    with patch("sys.argv", ["cli.py", dummy_input_file, "-c", dummy_config_yaml, "--dry-run"]):
        args = parse_args()
        assert args.input_file == os.path.abspath(dummy_input_file)
        assert args.extension == "ctf"
        assert args.basename == "test"


def test_parse_args_invalid_extension(temp_dir):

    from microtexture.cli import parse_args

    bad_file = os.path.join(temp_dir, "test.xyz")
    Path(bad_file).touch()

    with patch("sys.argv", ["cli.py", bad_file, "--dry-run"]):
        with pytest.raises(ValueError, match="Input file must be .ang or .ctf"):
            parse_args()


def test_render_template_valid(temp_dir, dummy_template, dummy_config_yaml, dummy_input_file):
    """Test rendering a valid Jinja2 template."""

    from microtexture.cli import parse_args, render_template

    with patch("sys.argv", ["cli.py", dummy_input_file, "-c", dummy_config_yaml, "--dry-run"]):
        args = parse_args()

    output_json = args.json_path
    context = vars(args)

    render_template(dummy_template, context, output_json)
    assert os.path.exists(output_json)
    with open(output_json, "r") as f:
        output = json.load(f)

    expected_json = files("microtexture") / "tests/dummy_render.json"
    expected = json.loads(expected_json.read_text().replace("TMP", temp_dir))

    assert output == expected


def test_render_template_invalid_json(temp_dir):
    """Test rendering template with invalid JSON output."""

    from microtexture.cli import render_template

    bad_template = os.path.join(temp_dir, "bad_template.j2")
    with open(bad_template, "w") as f:
        f.write("{ invalid json }")

    output_json = os.path.join(temp_dir, "output.json")
    context = {"input_file": "test.ang"}

    with pytest.raises(json.JSONDecodeError):
        render_template(bad_template, context, output_json)


def test_run_pipeline_success(temp_dir):
    """Test successful pipeline runner triggering."""

    from microtexture.cli import run_pipeline

    json_file = os.path.join(temp_dir, "pipeline.json")
    with open(json_file, "w") as f:
        json.dump({"test": "data"}, f)

    runner_path = Path(temp_dir) / "MockPipelineRunner"
    runner_path.touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        run_pipeline(json_file, runner_path)
        mock_run.assert_called_once_with(
            [runner_path, "-p", json_file], capture_output=True
        )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        run_pipeline(json_file, runner_path, verbose=True)
        mock_run.assert_called_once_with(
            [runner_path, "-p", json_file], capture_output=False
        )


def test_run_pipeline_runner_not_found(temp_dir):

    from microtexture.cli import run_pipeline

    json_file = os.path.join(temp_dir, "pipeline.json")
    runner_path = "/nonexistent/PipelineRunner"

    with pytest.raises(FileNotFoundError):
        run_pipeline(json_file, runner_path)


def test_run_pipeline_json_not_found(temp_dir):

    from microtexture.cli import run_pipeline

    json_file = os.path.join(temp_dir, "nonexistent.json")
    runner_path = "/fake/PipelineRunner"

    with pytest.raises(FileNotFoundError):
        run_pipeline(json_file, runner_path)


def test_run_pipeline_failure(temp_dir):
    """Test pipeline execution failure handling."""

    from microtexture.cli import run_pipeline

    json_file = Path(temp_dir) / "pipeline.json"
    runner_path = Path(temp_dir) / "PipelineRunner"

    json_file.touch()
    runner_path.touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout=b"out", stderr=b"err")
        with pytest.raises(RuntimeError):
            run_pipeline(json_file, runner_path)
