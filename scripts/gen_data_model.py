"""Generate the per-table data-model reference pages at docs-build time.

Run automatically by the ``mkdocs-gen-files`` plugin during ``mkdocs build``
(configured in ``mkdocs.yml``); it is not meant to be run by hand. Nothing it
writes is committed — the pages live only in the built site.

For every published table it reads the Frictionless **resource descriptor**
YAML (``eutl_scraper/publish/schemas/<table>.yaml``) referenced by that table's
publish config and renders a Markdown page under ``data/tables/`` containing:

- the table title + description,
- sources, primary key, and relationships as bold-keyword lines,
- a column table (Field / Type / Required / Key / Description).

It also extends ``data/data_model.md`` by appending a summary table (one row
per published table: title, one-line description, link).

A ``data/tables/SUMMARY.md`` nav file is emitted for ``mkdocs-literate-nav`` to
expand into the docs navigation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mkdocs_gen_files
import yaml

# gen-files executes this script via runpy, so the project root is not on
# sys.path; add it so the eutl_scraper package imports cleanly during the build.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eutl_scraper.publish.table_registry import TABLE_REGISTRY  # noqa: E402

TABLES_DIR = "data/tables"
# Physical landing page — read from the repo, extended with the summary table.
_LANDING_MD = Path(__file__).resolve().parent.parent / "docs" / "data" / "data_model.md"

# Placeholder in the landing page replaced by the generated ER diagram.
_DIAGRAM_PLACEHOLDER = "<!-- ER_DIAGRAM -->"

# Curated headline fields shown in the ER diagram on top of every primary- and
# foreign-key field. Keep this short — the diagram is a relationship overview,
# not a full column listing (those live on the per-table pages). Tables not
# listed here show their key fields only.
MAIN_FIELDS: dict[str, list[str]] = {
    "installations": ["name", "activity_name"],
    "accounts": ["name", "account_type"],
    "account_holders": ["name"],
    "projects": ["project_type"],
    "compliance": ["allocated", "verified", "surrendered"],
    "transactions": ["date", "transaction_type", "amount"],
    "installation_locations": ["latitude", "longitude"],
    "nace_mappings": ["nace_2015", "nace_2020"],
}


def as_list(value) -> list:
    """Coerce a scalar/list/None descriptor value into a list.

    Frictionless allows ``primaryKey`` and foreign-key ``fields`` to be either a
    single string or a list; normalise both to a list (and ``None`` to ``[]``).
    """
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def load_descriptors() -> dict[str, dict]:
    """Load every published table's resource descriptor, in registry order."""
    descriptors: dict[str, dict] = {}
    for name, config in TABLE_REGISTRY.items():
        descriptors[name] = yaml.safe_load(
            config.schema_path.read_text(encoding="utf-8")
        )
    return descriptors


def build_reverse_fk_index(
    descriptors: dict[str, dict],
) -> dict[str, list[tuple[str, str, str]]]:
    """Map each table to the inbound (source_table, source_field, target_field) FKs."""
    reverse: dict[str, list[tuple[str, str, str]]] = {}
    for source_table, descriptor in descriptors.items():
        for fk in descriptor["schema"].get("foreignKeys", []):
            target_table = fk["reference"]["resource"]
            source_fields = as_list(fk["fields"])
            target_fields = as_list(fk["reference"]["fields"])
            for src, tgt in zip(source_fields, target_fields):
                reverse.setdefault(target_table, []).append((source_table, src, tgt))
    return reverse


def render_page(
    name: str,
    descriptor: dict,
    reverse_fks: list[tuple[str, str, str]],
) -> str:
    """Render the Markdown reference page for a single table.

    Page order: title → description → sources → primary key →
    relationships (references / referenced by) → fields table.
    Sources, primary key, and relationships use bold-keyword inline style;
    the field table retains its ## heading for navigation anchoring.
    """
    schema = descriptor["schema"]
    fields = schema.get("fields", [])
    primary_key = as_list(schema.get("primaryKey"))
    foreign_keys = schema.get("foreignKeys", [])

    # Field names participating in a FK, for the Key column marker.
    fk_fields: set[str] = {f for fk in foreign_keys for f in as_list(fk["fields"])}

    lines: list[str] = [f"# {descriptor['title']}", ""]

    # Description.
    if descriptor.get("description"):
        lines += [descriptor["description"].strip(), ""]

    # Sources — bold keyword followed by a list.
    sources = descriptor.get("sources") or []
    if sources:
        lines.append("**Sources:**")
        lines.append("")
        for source in sources:
            title = source.get("title", "")
            path = source.get("path")
            lines.append(f"- [{title}]({path})" if path else f"- {title}")
        lines.append("")

    # Primary key — bold keyword inline.
    if primary_key:
        pk = ", ".join(f"`{c}`" for c in primary_key)
        lines += [f"**Primary key:** {pk}", ""]

    # Relationships — bold keyword per direction.
    references = []
    for fk in foreign_keys:
        target = fk["reference"]["resource"]
        for src, tgt in zip(as_list(fk["fields"]), as_list(fk["reference"]["fields"])):
            references.append(f"- `{src}` → [`{target}`]({target}.md) (`{tgt}`)")
    if references or reverse_fks:
        if references:
            lines += ["**References:**", ""]
            lines += references + [""]
        if reverse_fks:
            lines += ["**Referenced by:**", ""]
            for source_table, src, tgt in reverse_fks:
                lines.append(
                    f"- [`{source_table}`]({source_table}.md) (`{src}`) → `{tgt}`"
                )
            lines.append("")

    # Fields table — kept under a ## heading for anchor navigation.
    lines += [
        "## Fields",
        "",
        "| Field | Type | Required | Key | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for fld in fields:
        col = fld["name"]
        ftype = fld.get("type", "")
        required = "✓" if (fld.get("constraints") or {}).get("required") else ""
        markers = []
        if col in primary_key:
            markers.append("PK")
        if col in fk_fields:
            markers.append("FK")
        key = ", ".join(markers)
        # Collapse multi-line YAML descriptions to a single table cell line.
        desc = " ".join((fld.get("description") or fld.get("title") or "").split())
        lines.append(f"| `{col}` | {ftype} | {required} | {key} | {desc} |")
    lines.append("")

    return "\n".join(lines)


def render_er_diagram(
    descriptors: dict[str, dict],
    reverse_index: dict[str, list[tuple[str, str, str]]],
) -> str:
    """Render a Mermaid ``erDiagram`` of the FK-connected tables.

    A table is included iff it declares a foreign key or is the target of one
    (so standalone tables such as ``eex_auctions`` are dropped automatically).
    Each entity box lists its primary-key and foreign-key fields (marked
    ``PK``/``FK``) plus the curated headline fields in ``MAIN_FIELDS``; each FK
    is drawn as a ``target ||--o{ source`` edge labelled with the source field.
    """
    # Tables that participate in at least one relationship.
    connected = {
        name
        for name, descriptor in descriptors.items()
        if descriptor["schema"].get("foreignKeys")
    } | set(reverse_index)

    lines: list[str] = [
        "```mermaid",
        "%%{init: {'er': {'layoutDirection': 'TB'}}}%%",
        "erDiagram",
    ]

    # Entity boxes — registry order, connected tables only.
    for name, descriptor in descriptors.items():
        if name not in connected:
            continue
        schema = descriptor["schema"]
        fields = schema.get("fields", [])
        type_by_name = {f["name"]: f.get("type", "string") for f in fields}
        primary_key = as_list(schema.get("primaryKey"))
        fk_fields = [
            f for fk in schema.get("foreignKeys", []) for f in as_list(fk["fields"])
        ]

        # Attribute order: PK fields → FK-only fields → curated mains, deduped.
        ordered: list[str] = []
        for field in [*primary_key, *fk_fields, *MAIN_FIELDS.get(name, [])]:
            if field not in ordered and field in type_by_name:
                ordered.append(field)

        lines.append(f"    {name} {{")
        for field in ordered:
            markers = []
            if field in primary_key:
                markers.append("PK")
            if field in fk_fields:
                markers.append("FK")
            key = ", ".join(markers)
            lines.append(f"        {type_by_name[field]} {field} {key}".rstrip())
        lines.append("    }")

    # Relationships — one labelled edge per FK field.
    for name, descriptor in descriptors.items():
        for fk in descriptor["schema"].get("foreignKeys", []):
            target = fk["reference"]["resource"]
            for src in as_list(fk["fields"]):
                lines.append(f'    {target} ||--o{{ {name} : "{src}"')

    lines.append("```")
    return "\n".join(lines)


def render_summary_table(descriptors: dict[str, dict]) -> str:
    """Render a Markdown summary table: table title (linked) + one-line description."""
    rows = [
        "| Table | Description |",
        "| --- | --- |",
    ]
    for name, descriptor in descriptors.items():
        title = descriptor.get("title", name)
        # First sentence of the description, or the full description if short.
        desc_full = " ".join((descriptor.get("description") or "").split())
        desc = desc_full.split(".")[0] + "." if "." in desc_full else desc_full
        rows.append(f"| [{title}](tables/{name}.md) | {desc} |")
    return "\n".join(rows)


def main() -> None:
    descriptors = load_descriptors()
    reverse_index = build_reverse_fk_index(descriptors)

    # Per-table pages.
    nav = mkdocs_gen_files.Nav()
    for name, config in TABLE_REGISTRY.items():
        descriptor = descriptors[name]
        page_path = f"{TABLES_DIR}/{name}.md"
        content = render_page(name, descriptor, reverse_index.get(name, []))

        with mkdocs_gen_files.open(page_path, "w") as fd:
            fd.write(content)
        mkdocs_gen_files.set_edit_path(page_path, config.schema_path)

        nav[(descriptor["title"],)] = f"{name}.md"

    with mkdocs_gen_files.open(f"{TABLES_DIR}/SUMMARY.md", "w") as fd:
        fd.writelines(nav.build_literate_nav())

    # Landing page: hand-written intro + ER diagram + auto-generated summary table.
    intro = _LANDING_MD.read_text(encoding="utf-8").rstrip()
    diagram = render_er_diagram(descriptors, reverse_index)
    body = (
        intro.replace(_DIAGRAM_PLACEHOLDER, diagram)
        if _DIAGRAM_PLACEHOLDER in intro
        else f"{intro}\n\n{diagram}"
    )
    summary = render_summary_table(descriptors)
    with mkdocs_gen_files.open("data/data_model.md", "w") as fd:
        fd.write(f"{body}\n\n{summary}\n")


main()
