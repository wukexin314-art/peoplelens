#!/usr/bin/env python3
"""Unified command-line entry point for PeopleLens."""

from __future__ import annotations

import sys

import adapt_greenhouse
import analyze_opm_workforce_flow
import analyze_recruiting_funnel
import analyze_workforce
import profile_hr_data
import render_report


COMMANDS = {
    "profile": profile_hr_data.main,
    "funnel": analyze_recruiting_funnel.main,
    "workforce": analyze_workforce.main,
    "opm": analyze_opm_workforce_flow.main,
    "adapt-greenhouse": adapt_greenhouse.main,
    "report": render_report.main,
}


def print_help() -> None:
    print(
        """usage: peoplelens.py COMMAND [OPTIONS]

PeopleLens recruiting and workforce analytics.

commands:
  profile           Inspect data structure without printing raw values
  funnel            Analyze application stage-event history
  workforce         Analyze employee employment-spell data
  opm               Analyze OPM accessions and separations Parquet files
  adapt-greenhouse  Normalize a Greenhouse stage-changes CSV
  report            Render an aggregate output directory as HTML

Run `python3 scripts/peoplelens.py COMMAND --help` for command options.
"""
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print_help()
        return 0
    command = args.pop(0)
    if command not in COMMANDS:
        print(f"error: unknown command {command!r}", file=sys.stderr)
        print_help()
        return 2
    return COMMANDS[command](args)


if __name__ == "__main__":
    raise SystemExit(main())
