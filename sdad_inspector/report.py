from __future__ import annotations

import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import ReportError
from .paths import canonical_directory
from .snapshot import inspect_project


def _redact_strings(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        result = value
        for source, replacement in replacements:
            if source:
                result = result.replace(source, replacement)
        return result
    if isinstance(value, list):
        return [_redact_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _redact_strings(item, replacements) for key, item in value.items()}
    return value


def prepare_report_snapshot(
    snapshot: dict[str, Any],
    *,
    redact_paths: bool,
    redact_evidence: bool,
) -> dict[str, Any]:
    prepared = json.loads(json.dumps(snapshot, ensure_ascii=False))
    if redact_evidence:
        prepared["evidence"] = {
            "doctor_report": {"redacted": True},
            "doctor_exit_code": snapshot["doctor"]["exit_code"],
            "files": {
                path: {
                    "path": record.get("path"),
                    "exists": record.get("exists"),
                    "bytes": record.get("bytes"),
                    "redacted": True,
                }
                for path, record in snapshot.get("evidence", {}).get("files", {}).items()
            },
        }
        prepared["integrity"] = {
            "watched_control_paths": snapshot.get("integrity", {}).get(
                "watched_control_paths", []
            ),
            "control_files_unchanged_during_inspection": snapshot.get("integrity", {}).get(
                "control_files_unchanged_during_inspection", False
            ),
            "evidence_redacted": True,
        }
    if redact_paths:
        project_root = str(snapshot.get("project", {}).get("root", ""))
        engine_root = str(snapshot.get("engine", {}).get("checkout", ""))
        replacements = [
            (project_root, "<PROJECT_ROOT>"),
            (project_root.replace("\\", "/"), "<PROJECT_ROOT>"),
            (engine_root, "<SDAD_CHECKOUT>"),
            (engine_root.replace("\\", "/"), "<SDAD_CHECKOUT>"),
        ]
        prepared = _redact_strings(prepared, replacements)
    return prepared


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_static_report(
    snapshot: dict[str, Any],
    *,
    redact_paths: bool = False,
    redact_evidence: bool = False,
) -> str:
    data = prepare_report_snapshot(
        snapshot,
        redact_paths=redact_paths,
        redact_evidence=redact_evidence,
    )
    state = data["state"]
    packet = state.get("active_packet") or {}
    doctor = data["doctor"]
    project = data["project"]
    contracts = data["contracts"]
    validations = "".join(
        "<li><code>"
        + _escape(item["command"])
        + "</code><span>"
        + _escape(item["proves"])
        + "</span><strong>not executed</strong></li>"
        for item in state.get("validation", [])
    ) or '<li class="empty">No validation commands are declared.</li>'
    findings = "".join(
        "<li class=\"finding \" data-severity=\""
        + _escape(item.get("severity", "unknown"))
        + "\"><strong>"
        + _escape(item.get("id", "unknown"))
        + "</strong><span>"
        + _escape(item.get("message", ""))
        + "</span><code>"
        + _escape(item.get("path", ""))
        + (":" + _escape(item["line"]) if item.get("line") else "")
        + "</code><p>"
        + _escape(item.get("remediation", ""))
        + "</p></li>"
        for item in doctor.get("findings", [])
    ) or '<li class="empty">No Doctor findings were reported.</li>'
    gates = "".join(
        '<li><span class="gate-square"></span><span>'
        + _escape(gate)
        + "</span><strong>Stopped</strong></li>"
        for gate in state.get("owner_gates", [])
    ) or '<li class="empty">No owner gate is declared.</li>'
    limitations = "".join(
        "<li>" + _escape(item) + "</li>" for item in data.get("limitations", [])
    )
    raw_snapshot = _escape(json.dumps(data, ensure_ascii=False, indent=2))
    status = packet.get("status", "unavailable")
    csp = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
        "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{_escape(csp)}">
  <meta name="referrer" content="no-referrer">
  <title>SDAD Inspector Report — {_escape(project.get('name', 'project'))}</title>
  <style>
    :root {{ color:#10213f; background:#f7f9fc; font:14px/1.5 Inter,"Segoe UI",Arial,sans-serif; --line:#d8dee8; --blue:#0b64d8; --green:#24893e; --amber:#b86400; --red:#d21f2b; }}
    * {{ box-sizing:border-box }} body {{ margin:0; }} header {{ display:flex; align-items:center; gap:18px; min-height:58px; padding:0 24px; border-bottom:1px solid var(--line); background:#fff; }}
    header b {{ font-size:18px }} header code {{ overflow-wrap:anywhere; color:#344258 }} .readonly {{ margin-left:auto; font-weight:700 }}
    main {{ max-width:1320px; margin:0 auto; padding:28px 24px 56px }} .summary {{ display:grid; grid-template-columns:1.25fr .75fr; gap:22px; }}
    section {{ margin-bottom:22px; border:1px solid var(--line); background:#fff }} section>h2 {{ margin:0; padding:13px 16px; border-bottom:1px solid var(--line); font-size:15px }}
    .packet {{ padding:20px }} .kicker {{ margin:0 0 6px; color:#526176; font-weight:700 }} h1 {{ margin:0 0 16px; font-size:24px }} .status {{ color:var(--green); font-family:Consolas,monospace }}
    dl {{ display:grid; grid-template-columns:145px 1fr; margin:0 }} dt,dd {{ margin:0; padding:11px 14px; border-bottom:1px solid #e7ebf1 }} dt {{ color:#526176 }} dd {{ overflow-wrap:anywhere }}
    ul,ol {{ margin:0; padding:0; list-style:none }} .gates li,.validations li {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:6px 16px; padding:11px 14px; border-bottom:1px solid #e7ebf1 }}
    .gates li {{ grid-template-columns:14px minmax(0,1fr) auto }} .gate-square {{ width:9px; height:9px; margin-top:6px; background:var(--amber) }} .gates strong {{ color:var(--amber) }}
    .validations code {{ overflow-wrap:anywhere }} .validations span {{ grid-column:1; color:#526176; font-size:12px }} .validations strong {{ grid-column:2; grid-row:1/3; align-self:center; color:#526176; font-size:11px }}
    .findings li {{ display:grid; gap:5px; padding:12px 14px; border-bottom:1px solid #e7ebf1 }} .findings code {{ color:var(--blue) }} .findings p {{ margin:0; color:#526176 }} .empty {{ display:block!important; color:#526176 }}
    .limits {{ padding:12px 32px; list-style:disc }} .limits li {{ margin:5px 0 }} details {{ border:1px solid var(--line); background:#fff }} summary {{ padding:14px 16px; cursor:pointer; font-weight:700 }}
    pre {{ max-height:620px; margin:0; padding:16px; overflow:auto; border-top:1px solid var(--line); background:#f5f7fa; white-space:pre-wrap; overflow-wrap:anywhere; font:11px/1.5 Consolas,monospace }}
    footer {{ padding:18px 24px; color:#526176; border-top:1px solid var(--line); background:#fff; text-align:center; font-size:12px }}
    @media(max-width:800px) {{ .summary {{ grid-template-columns:1fr }} header {{ align-items:flex-start; flex-direction:column; gap:4px; padding:14px 18px }} .readonly {{ margin-left:0 }} main {{ padding:18px 12px 40px }} dl {{ grid-template-columns:115px 1fr }} }}
  </style>
</head>
<body data-read-only="true">
  <header><b>SDAD Inspector</b><code>{_escape(project.get('root', ''))}</code><span class="readonly">Read-only static report</span></header>
  <main>
    <div class="summary">
      <section><div class="packet"><p class="kicker">Active Packet</p><h1>{_escape(packet.get('id', 'Not declared'))}</h1><p class="status">{_escape(status)}</p><h2>Objective</h2><p>{_escape(packet.get('objective', 'No objective is declared.'))}</p></div></section>
      <section><h2>Provenance</h2><dl>
        <dt>Inspected at</dt><dd>{_escape(data.get('inspected_at'))}</dd>
        <dt>Doctor</dt><dd>{_escape(contracts.get('doctor_version'))}</dd>
        <dt>Report schema</dt><dd>{_escape(contracts.get('report_schema_version'))}</dd>
        <dt>State schema</dt><dd>{_escape(contracts.get('state_schema_version'))}</dd>
        <dt>Snapshot schema</dt><dd>{_escape(contracts.get('snapshot_schema_version'))}</dd>
        <dt>Doctor exit</dt><dd>{_escape(doctor.get('exit_code'))}</dd>
        <dt>Engine revision</dt><dd><code>{_escape(data['engine'].get('revision'))}</code></dd>
      </dl></section>
    </div>
    <section><h2>Doctor Summary — {_escape(doctor['summary']['errors'])} errors · {_escape(doctor['summary']['warnings'])} warnings</h2><ul class="findings">{findings}</ul></section>
    <section><h2>Stopped Owner Gates</h2><ul class="gates">{gates}</ul></section>
    <section><h2>Declared Validation Commands — presented, not executed</h2><ol class="validations">{validations}</ol></section>
    <section><h2>Limitations</h2><ul class="limits">{limitations}</ul></section>
    <details><summary>Normalized snapshot (escaped JSON)</summary><pre>{raw_snapshot}</pre></details>
  </main>
  <footer>Generated from snapshot {_escape(data.get('inspection_id'))}. This report does not execute commands or establish owner acceptance.</footer>
</body>
</html>
"""


def write_static_report(
    snapshot: dict[str, Any],
    output_path: str | Path,
    *,
    redact_paths: bool = False,
    redact_evidence: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    root = canonical_directory(snapshot["project"]["root"], label="Project root")
    supplied = Path(output_path).expanduser()
    if not supplied.name:
        raise ReportError("The report output must name one HTML file.")
    try:
        parent = supplied.parent.resolve(strict=True)
    except OSError as exc:
        raise ReportError(
            "The report output directory does not exist.", details={"path": str(supplied.parent)}
        ) from exc
    if not parent.is_dir():
        raise ReportError("The report output parent is not a directory.")
    output = parent / supplied.name
    try:
        output.resolve(strict=False).relative_to(root)
    except ValueError:
        pass
    else:
        raise ReportError(
            "Static reports must be written outside the inspected project.",
            details={"project_root": str(root)},
        )
    if output.exists() and output.is_symlink():
        raise ReportError("The report output cannot replace a symbolic link.")
    if output.exists() and not overwrite:
        raise ReportError(
            "The report output already exists; pass --overwrite to replace it.",
            details={"path": str(output)},
        )
    document = render_static_report(
        snapshot,
        redact_paths=redact_paths,
        redact_evidence=redact_evidence,
    )
    encoded = document.encode("utf-8")
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary_name, output)
            temporary_name = None
        else:
            try:
                os.link(temporary_name, output)
            except FileExistsError as exc:
                raise ReportError("The report output appeared during generation.") from exc
            os.unlink(temporary_name)
            temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
    return {
        "output": str(output),
        "bytes": len(encoded),
        "redact_paths": redact_paths,
        "redact_evidence": redact_evidence,
        "overwritten": overwrite,
    }


def generate_static_report(
    project_root: str | Path,
    sdad_checkout: str | Path,
    output_path: str | Path,
    *,
    redact_paths: bool = False,
    redact_evidence: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    snapshot = inspect_project(project_root, sdad_checkout)
    return write_static_report(
        snapshot,
        output_path,
        redact_paths=redact_paths,
        redact_evidence=redact_evidence,
        overwrite=overwrite,
    )
