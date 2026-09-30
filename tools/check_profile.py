import json
import os
import re
import sys
from importlib.metadata import version
from pathlib import Path
import yaml
from jupyter_client.kernelspec import KernelSpecManager


def require(condition, message):
    if not condition:
        raise SystemExit(message)


root = Path.cwd().resolve()
require(sys.implementation.name == "cpython", "CPython required")
require(sys.version_info[:3] == (3, 12, 14), "Python 3.12.14 required")
require(sys.prefix != sys.base_prefix, "Activate the project virtualenv")

for package, expected in {
    "jupyter-book": "2.1.7",
    "ipykernel": "7.3.0",
    "PyYAML": "6.0.3",
}.items():
    require(version(package) == expected, f"Wrong version: {package}")

require(version("jupyter-server"), "Jupyter Server required")

for name in ("JUPYTER_BASE_URL", "JUPYTER_TOKEN", "READTHEDOCS_CANONICAL_URL"):
    require(not os.environ.get(name), f"Unexpected environment override: {name}")

require("BASE_URL" in os.environ, "Set BASE_URL explicitly; empty is valid")
base = os.environ["BASE_URL"]
require(
    base == ""
    or (
        base.startswith("/")
        and not base.startswith("//")
        and not base.endswith("/")
        and not any(c in base for c in "?#\n\r")
    ),
    "BASE_URL must be empty or a path prefix such as /docs",
)

kernel_dir = Path(sys.prefix) / "share/jupyter/kernels/jb2-python"
spec = json.loads((kernel_dir / "kernel.json").read_text())
require(
    Path(spec["argv"][0]).absolute() == Path(sys.executable).absolute(),
    "Kernel does not launch this environment's Python",
)

resolved = KernelSpecManager().get_kernel_spec("jb2-python")
require(
    Path(resolved.resource_dir).resolve() == kernel_dir.resolve(),
    "Another kernelspec overrides the project kernel",
)


def local_file(value):
    require(isinstance(value, str), "Source path must be a string")
    path = root / value
    require(not Path(value).is_absolute(), f"Absolute source path: {value}")
    require(path.resolve().is_relative_to(root), f"External path: {value}")
    require(path.is_file(), f"Missing source or asset: {value}")
    return path


config = yaml.safe_load(Path("myst.yml").read_text())
require(
    isinstance(config, dict) and config.get("version") == 1,
    "Expected myst.yml version: 1",
)
require("extends" not in config, "Configuration inheritance needs a profile extension")
project = config.get("project", {})
require(not project.get("plugins"), "Custom plugins need a profile extension")
require(not project.get("exclude"), "Project exclusions are not accepted")

toc = project.get("toc")
require(isinstance(toc, list) and toc, "Explicit nonempty project.toc required")

site = config.get("site", {})
require(site.get("template") == "book-theme", "Expected book-theme selector")
local_file(site.get("options", {}).get("logo"))

files = []


def walk(entries):
    require(isinstance(entries, list), "TOC children must be a list")
    for entry in entries:
        require(isinstance(entry, dict), "TOC entry must be a mapping")
        require(
            set(entry) <= {"file", "title", "children"},
            "Unsupported TOC entry; use file/title/children",
        )
        require("file" in entry or entry.get("children"), "Empty TOC entry")
        if "file" in entry:
            files.append(local_file(entry["file"]))
        if "children" in entry:
            walk(entry["children"])


walk(toc)
require(len({p.resolve() for p in files}) == len(files), "Duplicate TOC file")

for path in Path("notebooks").rglob("*.ipynb"):
    if ".ipynb_checkpoints" not in path.parts:
        require(
            path.resolve() in {p.resolve() for p in files},
            f"Notebook absent from TOC: {path}",
        )

banned = {"skip-execution", "raises-exception"}


def check_controls(value, label):
    if isinstance(value, dict):
        execute = value.get("execute")
        if isinstance(execute, dict):
            require(execute.get("skip") in (None, False), f"Execution skipped: {label}")
        tags = value.get("tags", [])
        if isinstance(tags, (list, str)):
            require(not any(tag in tags for tag in banned), f"Forbidden tag: {label}")
        for child in value.values():
            check_controls(child, label)
    elif isinstance(value, list):
        for child in value:
            check_controls(child, label)


def check_kernel(metadata, label):
    expected = {
        "name": "jb2-python",
        "display_name": "Python (JB2)",
        "language": "python",
    }
    actual = metadata.get("kernelspec", {})
    require(
        all(actual.get(k) == v for k, v in expected.items()),
        f"Wrong or absent kernelspec: {label}",
    )


check_controls(config, "myst.yml")

for path in files:
    if path.suffix == ".ipynb":
        notebook = json.loads(path.read_text())
        check_controls(notebook.get("metadata", {}), path)
        cells = notebook.get("cells", [])
        for cell in cells:
            check_controls(cell.get("metadata", {}), path)
        computational = any(c.get("cell_type") == "code" for c in cells)
        computational = computational or any(
            "{ev" "al}" in "".join(c.get("source", []))
            or "{code-" "cell}" in "".join(c.get("source", []))
            for c in cells
            if c.get("cell_type") == "markdown"
        )
        if computational:
            check_kernel(notebook.get("metadata", {}), path)
    elif path.suffix == ".md":
        text = path.read_text()
        front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
        metadata = yaml.safe_load(front.group(1)) or {} if front else {}
        require(isinstance(metadata, dict), f"Invalid frontmatter: {path}")
        check_controls(metadata, path)
        if "{code-" "cell}" in text or "{ev" "al}" in text:
            check_kernel(metadata, path)
        require(
            not any(tag in text for tag in banned),
            f"Review executable Markdown execution controls: {path}",
        )

require(
    not Path("_config.yml").exists() and not Path("_toc.yml").exists(),
    "Remove legacy configuration from this profile",
)
print(f"Preflight passed for {len(files)} TOC files")
