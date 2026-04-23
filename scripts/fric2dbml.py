"""
Frictionless data package (.zip) -> DBML extractor.

Usage:
    python fric2dbml.py path/to/package.zip > schema.dbml

Then paste schema.dbml into https://dbdiagram.io, arrange tables visually,
and export SVG.
"""

import json
import sys
import zipfile
from pathlib import PurePosixPath

# Frictionless field types -> DBML types.
# DBML treats types as free-form labels, but a consistent mapping keeps
# the rendered diagram tidy.
TYPE_MAP = {
    "string": "varchar",
    "integer": "integer",
    "number": "decimal",
    "boolean": "boolean",
    "date": "date",
    "time": "time",
    "datetime": "datetime",
    "year": "integer",
    "yearmonth": "varchar",
    "duration": "varchar",
    "object": "json",
    "array": "json",
    "geopoint": "varchar",
    "geojson": "json",
    "any": "varchar",
}

# Optional per-table field hiding, for keeping the overview readable.
# Hidden fields are replaced by a single "..." placeholder row.
# Fill this in once you see the first rendered diagram.
HIDE_FIELDS: dict[str, set[str]] = {
    # "orders": {"internal_notes", "debug_payload", "raw_source"},
}


def as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def escape_note(text: str) -> str:
    return text.replace("'", "\\'").replace("\n", " ").strip()


def find_datapackage(zf: zipfile.ZipFile) -> str:
    """Locate datapackage.json, tolerating a wrapping directory."""
    candidates = [n for n in zf.namelist() if n.endswith("datapackage.json")]
    if not candidates:
        raise FileNotFoundError("datapackage.json not found in zip")
    # Prefer the shallowest match (handles both flat and prefixed packages).
    return min(candidates, key=lambda n: n.count("/"))


def load_schema(resource: dict, zf: zipfile.ZipFile, prefix: str) -> dict:
    """Schemas can be inline dicts or paths to separate JSON files."""
    schema = resource.get("schema")
    if isinstance(schema, str):
        path = str(PurePosixPath(prefix) / schema) if prefix else schema
        with zf.open(path) as f:
            return json.load(f)
    return schema or {}


def dbml_type(field: dict) -> str:
    return TYPE_MAP.get(field.get("type", "string"), "varchar")


def render_field(field: dict, pk_set: set, hidden: set) -> str | None:
    name = field["name"]
    if name in hidden:
        return None
    attrs = []
    # Single-column PKs are marked inline; composite PKs go in an indexes block.
    if name in pk_set and len(pk_set) == 1:
        attrs.append("pk")
    constraints = field.get("constraints") or {}
    if constraints.get("required"):
        attrs.append("not null")
    if constraints.get("unique"):
        attrs.append("unique")
    desc = field.get("description") or field.get("title")
    if desc:
        attrs.append(f"note: '{escape_note(desc)}'")
    suffix = f" [{', '.join(attrs)}]" if attrs else ""
    return f"  {name} {dbml_type(field)}{suffix}"


def render_table(resource: dict, schema: dict) -> str:
    name = resource["name"]
    fields = schema.get("fields", [])
    pk = set(as_list(schema.get("primaryKey")))
    hidden = HIDE_FIELDS.get(name, set())

    lines = [f"Table {name} {{"]
    for field in fields:
        line = render_field(field, pk, hidden)
        if line:
            lines.append(line)
    if hidden:
        lines.append(
            f"  \"...\" varchar [note: '{len(hidden)} field(s) omitted for overview']"
        )
    # Composite primary key
    if len(pk) > 1:
        # Preserve declaration order from the schema rather than sorting.
        ordered = [f["name"] for f in fields if f["name"] in pk]
        lines.append("  indexes {")
        lines.append(f"    ({', '.join(ordered)}) [pk]")
        lines.append("  }")
    # Table-level description as a DBML Note
    if resource.get("description"):
        lines.append(f"  Note: '{escape_note(resource['description'])}'")
    lines.append("}")
    return "\n".join(lines)


def render_refs(resources: list, schemas: dict) -> list[str]:
    lines = []
    for resource in resources:
        source = resource["name"]
        for fk in schemas[source].get("foreignKeys", []):
            src_fields = as_list(fk.get("fields"))
            ref = fk.get("reference") or {}
            # Empty / missing "resource" means a self-reference in Frictionless.
            target = ref.get("resource") or source
            tgt_fields = as_list(ref.get("fields"))
            if not src_fields or not tgt_fields:
                continue
            if len(src_fields) == 1:
                lines.append(
                    f"Ref: {source}.{src_fields[0]} > {target}.{tgt_fields[0]}"
                )
            else:
                s = ", ".join(src_fields)
                t = ", ".join(tgt_fields)
                lines.append(f"Ref: {source}.({s}) > {target}.({t})")
    return lines


def package_to_dbml(zip_path: str) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        dp_name = find_datapackage(zf)
        prefix = str(PurePosixPath(dp_name).parent) if "/" in dp_name else ""
        with zf.open(dp_name) as f:
            package = json.load(f)

        resources = package.get("resources", [])
        schemas = {r["name"]: load_schema(r, zf, prefix) for r in resources}

        chunks = []
        header = package.get("title") or package.get("name")
        if header:
            chunks.append(f"// Generated from: {header}")
        for resource in resources:
            chunks.append(render_table(resource, schemas[resource["name"]]))
        refs = render_refs(resources, schemas)
        if refs:
            chunks.append("\n".join(refs))
        return "\n\n".join(chunks)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fric2dbml.py <package.zip>", file=sys.stderr)
        sys.exit(1)
    print(package_to_dbml(sys.argv[1]))
