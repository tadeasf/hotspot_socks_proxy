"""Generate the code reference pages."""

from pathlib import Path

import mkdocs_gen_files
from mkdocs_gen_files.nav import Nav

# Create docs directory if it doesn't exist
docs_dir = Path("docs")
docs_dir.mkdir(exist_ok=True)

nav = Nav()

# Process Python files
for path in sorted(Path("src").rglob("*.py")):
    module_path = path.relative_to("src").with_suffix("")
    doc_path = path.relative_to("src").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"# {ident}\n\n")
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

# Generate navigation
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

# Add missing dependency to pyproject.toml or requirements.txt:
# mkdocs-gen-files>=0.5.0

# Create __init__.py in docs directory to fix namespace package warning
