#!/usr/bin/env python3
"""Render PeopleLens aggregate CSV outputs as a self-contained HTML report."""

from __future__ import annotations

import argparse
import csv
import html
import sys
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def optional_csv(directory: Path, name: str) -> list[dict[str, str]]:
    path = directory / name
    return read_csv(path) if path.is_file() else []


def esc(value: object) -> str:
    return html.escape(str(value))


def number(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0


def display_value(value: str, percent: bool = False) -> str:
    if not value:
        return "N/A"
    if percent:
        return f"{number(value):.1%}"
    numeric = number(value)
    if numeric == int(numeric):
        return f"{int(numeric):,}"
    return f"{numeric:,.2f}"


def label(value: str) -> str:
    return value.replace("_", " ").title()


# shortcut: fixed rule-of-thumb threshold, make it configurable if a team's policy differs.
DIRECTIONAL_SAMPLE_SIZE = 30


def protected_outcomes(rows: list[dict[str, str]], minimum: int) -> list[dict[str, str]]:
    # Stage drop-off totals are public in the funnel table, so any small cell hides the whole stage breakdown.
    result = []
    for stage in dict.fromkeys(row["stage"] for row in rows):
        group = [row for row in rows if row["stage"] == stage]
        if any(0 < int(row.get("application_count") or 0) < minimum for row in group):
            result.append({"stage": stage, "outcome": "detail protected", "application_count": "", "suppressed": "true"})
        else:
            result.extend(dict(row, suppressed=row.get("suppressed", "false")) for row in group)
    return result


def table(headers: list[str], rows: list[dict[str, str]], title: str) -> str:
    head = "".join(f"<th scope=col>{esc(label(header))}</th>" for header in headers)
    body = []
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(header, "")
            if header == "suppressed":
                value = (
                    '<span class="badge badge-private">Protected</span>'
                    if value == "true"
                    else '<span class="badge badge-clear">Visible</span>'
                )
                cells.append(f"<td>{value}</td>")
            elif header.endswith("_rate") and value:
                cells.append(f"<td class=num>{esc(display_value(value, True))}</td>")
            else:
                cells.append(f"<td>{esc(value or '—')}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<div class=table-wrap role=region aria-label="{esc(title)}" tabindex=0>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def card(label_text: str, value: str, caption: str, tone: str = "") -> str:
    return (
        f'<article class="metric-card {esc(tone)}"><span>{esc(label_text)}</span>'
        f"<strong>{esc(value or 'N/A')}</strong><small>{esc(caption)}</small></article>"
    )


def section(title: str, eyebrow: str, body: str, note: str = "") -> str:
    note_html = f"<p class=section-note>{esc(note)}</p>" if note else ""
    return (
        f"<section><div class=section-head><div><span>{esc(eyebrow)}</span>"
        f"<h2>{esc(title)}</h2></div>{note_html}</div>{body}</section>"
    )


def quality_panel(directory: Path) -> str:
    rows = optional_csv(directory, "data_quality.csv")
    errors = sum(int(row.get("count", "0")) for row in rows if row.get("severity") == "error")
    warnings = sum(int(row.get("count", "0")) for row in rows if row.get("severity") == "warning")
    active = [row for row in rows if int(row.get("count", "0")) > 0]
    if errors:
        status, tone, message = "Action required", "danger", f"{errors} errors and {warnings} warnings"
    elif warnings:
        status, tone, message = "Review advised", "warn", f"{warnings} warnings; no blocking errors"
    else:
        status, tone, message = "Checks clear", "success", f"{len(rows)} checks completed with no flagged records"
    items = "".join(
        f"<li><b>{esc(label(row['check']))}</b><span>{esc(row['count'])}</span><small>{esc(row['detail'])}</small></li>"
        for row in active[:6]
    )
    detail = f"<ul class=quality-list>{items}</ul>" if items else "<p class=quiet>No active data-quality exceptions in this run.</p>"
    return (
        f'<div class="quality-summary {tone}"><div class=status-mark aria-hidden=true></div>'
        f"<div><span>Data quality</span><strong>{esc(status)}</strong><small>{esc(message)}</small></div></div>{detail}"
    )


def render_funnel(directory: Path) -> tuple[str, str, str, str]:
    rows = read_csv(directory / "funnel_summary.csv")
    cohort = optional_csv(directory, "cohort_summary.csv")
    outcomes = optional_csv(directory, "stage_outcomes.csv")
    segment_rows = optional_csv(directory, "segment_summary.csv")
    minimum_cell_size = int(segment_rows[0].get("minimum_cell_size", "5")) if segment_rows else 5
    outcomes = protected_outcomes(outcomes, minimum_cell_size)
    first = rows[0] if rows else {}
    last = rows[-1] if rows else {}
    applications = int(first.get("reached_applications", "0"))
    starts = int(last.get("reached_applications", "0"))
    yield_rate = starts / applications if applications else 0
    backlog = sum(int(row.get("active_backlog", "0")) for row in rows)
    maximum = max((int(row["reached_applications"]) for row in rows), default=1)
    adjacent = [row for row in rows if row.get("adjacent_conversion_rate")]
    bottleneck = min(adjacent, key=lambda row: number(row["adjacent_conversion_rate"])) if adjacent else None
    bottleneck_n = int(bottleneck["reached_applications"]) if bottleneck else 0
    small_note = f" · n={bottleneck_n}, directional" if bottleneck and bottleneck_n < DIRECTIONAL_SAMPLE_SIZE else ""
    longest = max(rows, key=lambda row: number(row.get("median_time_in_stage_days"))) if rows else None

    cards = "".join(
        [
            card("Applications", f"{applications:,}", "Mature entry cohort"),
            card("Starts", f"{starts:,}", f"{yield_rate:.1%} application-to-start", "accent"),
            card("Active backlog", f"{backlog:,}", "Open at the as-of date", "warm"),
            card(
                "Primary bottleneck",
                label(bottleneck["stage"]) if bottleneck else "N/A",
                f"{number(bottleneck['adjacent_conversion_rate']):.1%} next-stage conversion{small_note}" if bottleneck else "No comparable stages",
            ),
        ]
    )

    journey = []
    for index, row in enumerate(rows, 1):
        reached = int(row["reached_applications"])
        conversion = row.get("adjacent_conversion_rate", "")
        width = reached / maximum * 100 if maximum else 0
        stage_label = label(row["stage"])
        conversion_label = display_value(conversion, True) if conversion else "Final stage"
        median_days = row.get("median_time_in_stage_days") or "—"
        active_backlog = row.get("active_backlog") or "0"
        journey.append(
            f'<article class=stage-row><div class=stage-name><i>{index:02d}</i><div><strong>{esc(stage_label)}</strong>'
            f'<small>{reached:,} reached</small></div></div><div class=stage-visual><div class=bar-track aria-label="{esc(stage_label)}: {reached} applications">'
            f'<span style="width:{width:.1f}%"></span></div><div class=stage-meta><span>{esc(conversion_label)}</span>'
            f'<span>{esc(median_days)} median days</span><span>{esc(active_backlog)} backlog</span></div></div></article>'
        )

    insight_items = []
    if bottleneck:
        insight_items.append(
            f"<li><span>Bottleneck</span><strong>{esc(label(bottleneck['stage']))} converts at {number(bottleneck['adjacent_conversion_rate']):.1%}{esc(small_note)}</strong></li>"
        )
    if longest and longest.get("median_time_in_stage_days"):
        insight_items.append(
            f"<li><span>Longest median stage</span><strong>{esc(label(longest['stage']))} · {esc(longest['median_time_in_stage_days'])} days</strong></li>"
        )
    insight_items.append(f"<li><span>End-to-end yield</span><strong>{yield_rate:.1%} of mature applications started</strong></li>")
    insights = f"<ul class=insight-list>{''.join(insight_items)}</ul>"

    outcome_body = (
        table(["stage", "outcome", "application_count", "suppressed"], outcomes, "Stage outcomes")
        if outcomes
        else "<p class=quiet>No terminal outcomes were recorded.</p>"
    )
    cohort_note = ""
    if cohort:
        item = cohort[0]
        cohort_note = f"Cohort {item.get('start_date') or 'open'} to {item.get('end_date') or 'open'} · {item.get('mature_applications', '0')} mature applications"
    scope = cohort_note or "Mature recruiting cohort"
    bottleneck_label = label(bottleneck["stage"]) if bottleneck else "the lowest-converting stage"
    small_caveat = f" Only {bottleneck_n} applications reached this stage, so treat the ranking as directional." if small_note else ""
    content = (
        f'<div class=decision-strip><span>Decision snapshot</span><p>The lowest adjacent conversion begins at <b>{esc(bottleneck_label)}</b>; review this transition while monitoring {backlog:,} active records.{esc(small_caveat)}</p></div>'
        f"<div class=metric-grid>{cards}</div>"
        + section("Candidate journey", "Funnel", "".join(journey), "Stage reach, speed, and active backlog")
        + f'<div class=two-col>{section("What stands out", "Interpretation", insights)}{section("Quality gate", "Trust", quality_panel(directory))}</div>'
        + section("Terminal outcomes", "Diagnostics", outcome_body, "Counts by the stage where the application ended")
        + section(
            "Detailed metric table",
            "Audit trail",
            table(["stage", "reached_applications", "adjacent_conversion_rate", "cumulative_yield_rate", "terminal_drop_offs", "active_backlog", "median_time_in_stage_days", "p75_time_in_stage_days"], rows, "Funnel detail"),
        )
    )
    return "Recruiting funnel", "Talent acquisition", scope, content


def render_workforce(directory: Path) -> tuple[str, str, str, str]:
    metrics = read_csv(directory / "workforce_metrics.csv")
    lookup = {row["metric_name"]: row["value"] for row in metrics}
    first = metrics[0] if metrics else {}
    opening = number(lookup.get("opening_headcount"))
    closing = number(lookup.get("closing_headcount"))
    hires = number(lookup.get("period_hires"))
    separations = number(lookup.get("period_separations"))
    growth = number(lookup.get("headcount_growth_rate"))
    turnover = number(lookup.get("turnover_rate"))
    voluntary = number(lookup.get("voluntary_turnover_rate"))
    involuntary = number(lookup.get("involuntary_turnover_rate"))
    retention_name = next((name for name in lookup if name.startswith("retention_") and name.endswith("_day_rate")), "")
    retention = number(lookup.get(retention_name))
    retention_days = retention_name.removeprefix("retention_").removesuffix("_day_rate") if retention_name else "N"
    scope = f"{first.get('period_start', 'Period start')} to {first.get('period_end', 'Period end')} · as of {first.get('as_of_date', 'N/A')}"

    cards = "".join(
        [
            card("Closing headcount", display_value(lookup.get("closing_headcount", "")), f"{growth:+.1%} versus opening", "accent"),
            card("Period hires", display_value(lookup.get("period_hires", "")), "Employment spells starting in period"),
            card("Period separations", display_value(lookup.get("period_separations", "")), "Effective separations in period", "warm"),
            card("Turnover", display_value(lookup.get("turnover_rate", ""), True), "Using approximate average headcount"),
            card("Closing FTE", display_value(lookup.get("closing_fte", "")), "Active workforce capacity"),
            card(f"{retention_days}-day retention", display_value(lookup.get(retention_name, ""), True), "Mature hire cohort"),
        ]
    )

    movement_max = max(opening, closing, hires, separations, 1)
    movement = "".join(
        [
            f'<div class="movement opening"><span>Opening</span><strong>{opening:,.0f}</strong><i style="height:{max(12, opening / movement_max * 100):.1f}%"></i></div>',
            f'<div class="movement positive"><span>Hires</span><strong>+{hires:,.0f}</strong><i style="height:{max(12, hires / movement_max * 100):.1f}%"></i></div>',
            f'<div class="movement negative"><span>Separations</span><strong>−{separations:,.0f}</strong><i style="height:{max(12, separations / movement_max * 100):.1f}%"></i></div>',
            f'<div class="movement closing"><span>Closing</span><strong>{closing:,.0f}</strong><i style="height:{max(12, closing / movement_max * 100):.1f}%"></i></div>',
        ]
    )

    separation_types = optional_csv(directory, "separation_summary.csv")
    composition_protected = any(row.get("suppressed") == "true" for row in separation_types)
    if composition_protected:
        composition = (
            '<div class=protected-panel><div class=lock-mark aria-hidden=true>×</div><strong>Breakdown protected</strong>'
            '<p>Voluntary and involuntary composition is hidden because one or more cells fall below the configured privacy threshold.</p></div>'
        )
    else:
        voluntary_share = voluntary / turnover if turnover else 0
        involuntary_share = involuntary / turnover if turnover else 0
        donut_end = min(100, (voluntary_share + involuntary_share) * 100)
        composition = (
            f'<div class=donut style="--vol:{voluntary_share * 100:.1f}%;--end:{donut_end:.1f}%"><div><strong>{turnover:.1%}</strong><span>Total turnover</span></div></div>'
            f'<ul class=legend><li><i class=voluntary></i><span>Voluntary</span><strong>{voluntary:.1%}</strong></li>'
            f'<li><i class=involuntary></i><span>Involuntary</span><strong>{involuntary:.1%}</strong></li></ul>'
        )
    retention_panel = (
        f'<div class=retention-score><strong>{retention:.1%}</strong><span>{esc(retention_days)}-day mature-cohort retention</span></div>'
        f'<div class=progress role=progressbar aria-label="{esc(retention_days)}-day retention" aria-valuemin=0 aria-valuemax=100 aria-valuenow="{retention * 100:.1f}"><span style="width:{max(0, min(100, retention * 100)):.1f}%"></span></div>'
        '<p class=quiet>Immature hires remain outside the denominator until the full observation window has elapsed.</p>'
    )

    segments = optional_csv(directory, "segment_summary.csv")
    segment_body = table(["segment", "value", "opening_headcount", "closing_headcount", "period_hires", "period_separations", "turnover_rate", "suppressed"], segments, "Workforce segments") if segments else "<p class=quiet>No segment output was configured.</p>"
    separation_body = table(["separation_type", "separation_count", "share_of_separations", "suppressed"], separation_types, "Separation mix") if separation_types else "<p class=quiet>No period separations were recorded.</p>"
    movement_body = f"<div class=movement-chart>{movement}</div>"
    display_metrics = [dict(row) for row in metrics]
    if composition_protected:
        for row in display_metrics:
            if row["metric_name"] in {"voluntary_turnover_rate", "involuntary_turnover_rate"}:
                row.update(value="", numerator="", denominator="")
    metric_body = table(["metric_name", "value", "numerator", "denominator"], display_metrics, "Workforce metrics")
    content = (
        f'<div class=decision-strip><span>Decision snapshot</span><p>Headcount closed at <b>{closing:,.0f}</b>, a <b>{growth:+.1%}</b> change from opening. Hiring exceeded separations by <b>{hires - separations:+,.0f}</b> employment spells.</p></div>'
        f"<div class=metric-grid>{cards}</div>"
        + f'<div class=two-col>{section("Workforce movement", "Flow", movement_body, "Opening + hires − separations = closing")}{section("Turnover composition", "Separation", composition)}</div>'
        + f'<div class=two-col>{section("Cohort retention", "Outcome", retention_panel)}{section("Quality gate", "Trust", quality_panel(directory))}</div>'
        + section("Workforce segments", "Privacy-aware detail", segment_body, "Protected cells are intentionally blank")
        + f'<div class=two-col wide-left>{section("Metric definitions in use", "Audit trail", metric_body)}{section("Separation mix", "Diagnostics", separation_body)}</div>'
    )
    return "Workforce overview", "People analytics", scope, content


def render(input_dir: Path, output: Path, title: str | None = None, force: bool = False) -> None:
    if output.exists() and not force:
        raise FileExistsError(f"Output already exists: {output}. Use --force to replace it.")
    if (input_dir / "funnel_summary.csv").is_file():
        default_title, category, scope, content = render_funnel(input_dir)
    elif (input_dir / "workforce_metrics.csv").is_file():
        default_title, category, scope, content = render_workforce(input_dir)
    else:
        raise ValueError("Input directory must contain funnel_summary.csv or workforce_metrics.csv")
    report_title = title or default_title
    document = f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<meta name=description content="Privacy-aware PeopleLens HR analytics report"><title>{esc(report_title)}</title><style>
:root{{--ink:#14232b;--muted:#61727a;--faint:#8a989e;--line:#dce5e5;--paper:#fff;--bg:#eef3f2;--navy:#173f4f;--teal:#0d8b7d;--teal-soft:#dff3ee;--blue:#3e6fb4;--coral:#e36d52;--amber:#b87718;--danger:#b8463a;--shadow:0 12px 32px rgba(24,58,66,.08)}}
*{{box-sizing:border-box}}html{{background:var(--bg)}}body{{margin:0;color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;background:radial-gradient(circle at 85% -10%,#d2ebe5 0,transparent 32rem),var(--bg)}}main{{max-width:1180px;margin:auto;padding:34px 26px 56px}}.topbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:44px}}.brand{{display:flex;align-items:center;gap:11px;font-weight:800;letter-spacing:-.02em}}.brand-mark{{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;color:white;background:linear-gradient(145deg,var(--navy),var(--teal));box-shadow:0 7px 18px rgba(13,139,125,.23)}}.brand small{{display:block;color:var(--muted);font-size:10px;font-weight:650;letter-spacing:.12em;text-transform:uppercase}}.privacy{{display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid #bedbd5;border-radius:999px;background:rgba(255,255,255,.7);color:#176e64;font-size:12px;font-weight:700}}.privacy:before{{content:"";width:7px;height:7px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 4px rgba(13,139,125,.12)}}header{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:28px;align-items:end;margin-bottom:28px}}.eyebrow{{color:var(--teal);font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}}h1{{font-size:clamp(34px,6vw,62px);line-height:1.02;letter-spacing:-.055em;margin:7px 0 11px;max-width:790px}}.scope{{color:var(--muted);margin:0;font-size:14px}}.run-label{{padding:13px 16px;border-left:2px solid var(--teal);color:var(--muted);font-size:12px;max-width:230px}}.run-label strong{{display:block;color:var(--ink);font-size:13px}}.decision-strip{{display:grid;grid-template-columns:150px 1fr;gap:18px;align-items:center;background:var(--navy);color:#eaf4f2;border-radius:18px;padding:20px 24px;box-shadow:var(--shadow)}}.decision-strip span{{color:#78d2c5;font-size:11px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}.decision-strip p{{margin:0;font-size:16px}}.metric-grid{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:18px 0}}.metric-card{{min-height:132px;background:rgba(255,255,255,.88);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 4px 16px rgba(28,56,63,.035)}}.metric-card span{{display:block;color:var(--muted);font-size:11px;font-weight:800;letter-spacing:.07em;text-transform:uppercase}}.metric-card strong{{display:block;margin:14px 0 5px;font-size:28px;line-height:1;letter-spacing:-.04em}}.metric-card small{{display:block;color:var(--faint);font-size:11px;line-height:1.35}}.metric-card.accent{{border-color:#a7d8ce;background:linear-gradient(150deg,#fff,#e6f7f2)}}.metric-card.warm{{border-color:#f1c9bc;background:linear-gradient(150deg,#fff,#fff0eb)}}section{{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:18px;padding:24px;margin:16px 0;box-shadow:0 4px 20px rgba(28,56,63,.035)}}.section-head{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:20px}}.section-head span{{display:block;color:var(--teal);font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}h2{{font-size:21px;line-height:1.2;margin:5px 0 0;letter-spacing:-.02em}}.section-note{{color:var(--muted);font-size:12px;margin:0;text-align:right}}.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.two-col section{{margin:0}}.wide-left{{grid-template-columns:1.5fr 1fr}}.stage-row{{display:grid;grid-template-columns:190px 1fr;gap:22px;align-items:center;padding:15px 0;border-bottom:1px solid #e7eded}}.stage-row:last-child{{border:0}}.stage-name{{display:flex;gap:12px;align-items:center}}.stage-name i{{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:#edf5f3;color:var(--teal);font-size:11px;font-style:normal;font-weight:800}}.stage-name strong,.stage-name small{{display:block}}.stage-name small{{color:var(--muted);font-size:11px}}.bar-track{{height:13px;background:#e8efee;border-radius:99px;overflow:hidden}}.bar-track span{{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--navy),var(--teal))}}.stage-meta{{display:flex;gap:18px;margin-top:7px;color:var(--muted);font-size:11px}}.stage-meta span:first-child{{color:var(--ink);font-weight:750}}.insight-list,.quality-list,.legend{{list-style:none;padding:0;margin:0}}.insight-list li{{display:grid;grid-template-columns:125px 1fr;gap:14px;padding:14px 0;border-bottom:1px solid var(--line)}}.insight-list li:last-child{{border:0}}.insight-list span{{color:var(--muted);font-size:12px}}.insight-list strong{{font-size:14px}}.quality-summary{{display:flex;gap:14px;align-items:center;padding:16px;border-radius:14px;background:#edf6f3}}.quality-summary.warn{{background:#fff6e6}}.quality-summary.danger{{background:#fff0ed}}.status-mark{{width:12px;height:12px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 6px rgba(13,139,125,.13)}}.warn .status-mark{{background:var(--amber);box-shadow:0 0 0 6px rgba(184,119,24,.12)}}.danger .status-mark{{background:var(--danger);box-shadow:0 0 0 6px rgba(184,70,58,.12)}}.quality-summary span,.quality-summary strong,.quality-summary small{{display:block}}.quality-summary span{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.1em}}.quality-summary strong{{font-size:18px}}.quality-summary small{{color:var(--muted)}}.quality-list li{{display:grid;grid-template-columns:1fr auto;gap:5px 15px;padding:12px 0;border-bottom:1px solid var(--line)}}.quality-list li small{{grid-column:1/-1;color:var(--muted)}}.quiet{{color:var(--muted);font-size:13px;margin:15px 0 0}}.movement-chart{{height:245px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;align-items:end;padding:8px 8px 0}}.movement{{height:100%;display:flex;flex-direction:column;justify-content:end;text-align:center}}.movement span{{color:var(--muted);font-size:11px;order:3;margin-top:7px}}.movement strong{{font-size:18px;order:2;margin-top:7px}}.movement i{{display:block;order:1;min-height:20px;border-radius:10px 10px 3px 3px;background:#9fb4b9}}.movement.positive i{{background:linear-gradient(#5bc0ae,var(--teal))}}.movement.negative i{{background:linear-gradient(#efa18b,var(--coral))}}.movement.closing i{{background:linear-gradient(#527b8b,var(--navy))}}.donut{{--vol:50%;--end:100%;width:180px;height:180px;margin:5px auto 24px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--teal) 0 var(--vol),var(--coral) var(--vol) var(--end),#dce5e5 var(--end) 100%);position:relative}}.donut:after{{content:"";position:absolute;inset:24px;border-radius:50%;background:white}}.donut div{{position:relative;z-index:1;text-align:center}}.donut strong,.donut span{{display:block}}.donut strong{{font-size:29px}}.donut span{{color:var(--muted);font-size:11px}}.legend li{{display:grid;grid-template-columns:10px 1fr auto;gap:9px;align-items:center;padding:8px 0}}.legend i{{width:9px;height:9px;border-radius:3px;background:var(--teal)}}.legend i.involuntary{{background:var(--coral)}}.legend span{{color:var(--muted)}}.protected-panel{{min-height:250px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:25px}}.protected-panel .lock-mark{{display:grid;place-items:center;width:54px;height:54px;border-radius:16px;background:#fff0e9;color:#a64f37;font-size:28px;transform:rotate(45deg);margin-bottom:16px}}.protected-panel .lock-mark::first-letter{{transform:rotate(-45deg)}}.protected-panel strong{{font-size:18px}}.protected-panel p{{max-width:370px;color:var(--muted);font-size:12px}}.retention-score strong{{display:block;font-size:44px;letter-spacing:-.05em}}.retention-score span{{color:var(--muted)}}.progress{{height:14px;background:#e4ecea;border-radius:99px;overflow:hidden;margin:20px 0 0}}.progress span{{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--navy),var(--teal))}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:11px 12px;border-bottom:1px solid #e6ecec;text-align:left;white-space:nowrap}}th{{background:#f5f8f7;color:var(--muted);font-size:9px;letter-spacing:.08em;text-transform:uppercase;position:sticky;top:0}}tbody tr:last-child td{{border:0}}tbody tr:hover{{background:#f8fbfa}}td.num{{font-variant-numeric:tabular-nums}}.badge{{display:inline-block;padding:4px 7px;border-radius:6px;font-size:9px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}}.badge-private{{background:#fff0e9;color:#a64f37}}.badge-clear{{background:#e5f4ef;color:#176e64}}footer{{display:grid;grid-template-columns:1fr auto;gap:24px;margin-top:28px;padding:22px 3px;color:var(--muted);font-size:11px;border-top:1px solid #cfdbda}}footer strong{{color:var(--navy)}}
@media(max-width:980px){{.metric-grid{{grid-template-columns:repeat(3,1fr)}}.two-col,.wide-left{{grid-template-columns:1fr}}}}
@media(max-width:650px){{main{{padding:22px 14px 38px}}.topbar{{margin-bottom:28px}}header{{grid-template-columns:1fr}}.run-label{{display:none}}.decision-strip{{grid-template-columns:1fr;gap:5px}}.metric-grid{{grid-template-columns:repeat(2,1fr)}}.stage-row{{grid-template-columns:1fr;gap:10px}}.stage-meta{{justify-content:space-between;gap:8px}}.section-head{{display:block}}.section-note{{text-align:left;margin-top:6px}}.movement-chart{{height:210px;padding:0}}footer{{grid-template-columns:1fr}}}}
@media print{{:root{{--bg:#fff}}body{{background:#fff}}main{{max-width:none;padding:0}}.topbar{{margin-bottom:24px}}section,.metric-card,.decision-strip{{box-shadow:none;break-inside:avoid}}.table-wrap{{overflow:visible}}th{{position:static}}}}
</style></head><body><main><div class=topbar><div class=brand><div class=brand-mark aria-hidden=true>PL</div><div>PeopleLens<small>HR analytics</small></div></div><div class=privacy>Aggregate &amp; privacy-aware</div></div>
<header><div><span class=eyebrow>{esc(category)}</span><h1>{esc(report_title)}</h1><p class=scope>{esc(scope)}</p></div><div class=run-label><strong>Decision-ready output</strong>Metrics, diagnostics, and method context in one self-contained report.</div></header>
{content}<footer><span><strong>PeopleLens methodology:</strong> trace every rate to its population, numerator, denominator, and observation window.</span><span>Review the accompanying quality, cohort, mapping, and metric-dictionary files before making decisions.</span></footer></main></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="PeopleLens aggregate output directory")
    parser.add_argument("--output", type=Path, required=True, help="HTML report path")
    parser.add_argument("--title", help="Optional report title")
    parser.add_argument("--force", action="store_true", help="Replace the report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        render(args.input_dir, args.output, args.title, args.force)
        print(args.output)
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
