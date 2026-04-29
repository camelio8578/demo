"""CLI entry point for Proceeds Navigator."""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from proceeds_navigator.db.models import Lead, ScrapeRun
from proceeds_navigator.db.session import get_engine, get_session_factory, init_db
from proceeds_navigator.etl.deduplicator import Deduplicator
from proceeds_navigator.etl.enricher import Enricher
from proceeds_navigator.etl.normalizer import Normalizer, ParseError
from proceeds_navigator.scoring.explainer import explanation_to_json
from proceeds_navigator.scoring.scorer import LeadScorer

log = structlog.get_logger()
app = typer.Typer(name="proceeds-navigator", help="Proceeds Navigator CLI")
console = Console()

VALID_COUNTIES = ["fresno", "san_diego", "sacramento", "los_angeles"]


def _get_db() -> Session:
    init_db()
    factory = get_session_factory()
    return factory()


@app.command()
def scrape(
    county: Optional[str] = typer.Option(None, "--county", "-c", help="County to scrape (default: all)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse and print results without saving"),
) -> None:
    """Scrape county public records for excess proceeds leads."""
    from proceeds_navigator.scraper.counties import COUNTY_SCRAPERS

    counties_to_run = [county] if county else VALID_COUNTIES
    for c in counties_to_run:
        if c not in COUNTY_SCRAPERS:
            console.print(f"[red]Unknown county: {c}. Valid: {', '.join(VALID_COUNTIES)}[/red]")
            raise typer.Exit(1)

    normalizer = Normalizer()
    enricher = Enricher()
    deduper = Deduplicator()
    scorer = LeadScorer()

    db = _get_db()
    try:
        existing_hashes = {
            row[0] for row in db.query(Lead.content_hash).filter(Lead.content_hash.isnot(None)).all()
        }

        for county_key in counties_to_run:
            console.print(f"\n[bold cyan]Scraping {county_key}...[/bold cyan]")
            scraper_cls = COUNTY_SCRAPERS[county_key]
            scraper = scraper_cls()
            run_start = datetime.utcnow()
            all_results = scraper.scrape()

            total_found = 0
            total_new = 0
            total_errors = 0
            snapshot_path: Optional[str] = None

            for result in all_results:
                total_errors += len(result.errors)
                if result.snapshot_path:
                    snapshot_path = str(result.snapshot_path)

                for raw in result.raw_leads:
                    try:
                        normalized = normalizer.normalize(raw)
                        normalized = enricher.enrich(normalized)
                        content_hash = deduper.compute_hash(normalized)
                        normalized["content_hash"] = content_hash
                        total_found += 1

                        if content_hash in existing_hashes:
                            continue

                        score_result = scorer.score(normalized)
                        normalized["score"] = score_result.score
                        normalized["priority_rank"] = score_result.priority_rank
                        normalized["legal_risk_flag"] = score_result.legal_risk_flag
                        normalized["score_explanation"] = explanation_to_json(score_result.explanation)
                        normalized["last_checked_at"] = datetime.utcnow()

                        if dry_run:
                            console.print(f"  [green]WOULD INSERT:[/green] APN={normalized.get('parcel_apn')} score={score_result.score:.1f} risk={score_result.legal_risk_flag}")
                        else:
                            lead = Lead(**{
                                k: v for k, v in normalized.items()
                                if hasattr(Lead, k)
                            })
                            db.add(lead)
                            existing_hashes.add(content_hash)
                            total_new += 1

                    except ParseError as exc:
                        log.warning("normalize_error", county=county_key, error=str(exc))
                        total_errors += 1
                    except Exception as exc:
                        log.error("lead_insert_error", county=county_key, error=str(exc))
                        total_errors += 1

                if result.errors:
                    for err in result.errors:
                        console.print(f"  [yellow]⚠ {err}[/yellow]")

            if not dry_run:
                db.commit()
                run = ScrapeRun(
                    county=county_key,
                    started_at=run_start,
                    completed_at=datetime.utcnow(),
                    leads_found=total_found,
                    leads_new=total_new,
                    error_count=total_errors,
                    status="success" if not total_errors else ("partial" if total_found else "failed"),
                    snapshot_path=snapshot_path,
                )
                db.add(run)
                db.commit()

            console.print(
                f"  Found: {total_found} | New: {total_new} | Errors: {total_errors}"
                + (" [DRY RUN]" if dry_run else "")
            )
    finally:
        db.close()


@app.command()
def score(
    lead_id: Optional[int] = typer.Option(None, "--id", help="Score a specific lead by ID"),
    all_leads: bool = typer.Option(False, "--all", help="Rescore all leads"),
) -> None:
    """Compute or recompute lead scores."""
    if not lead_id and not all_leads:
        console.print("[red]Specify --id <id> or --all[/red]")
        raise typer.Exit(1)

    scorer = LeadScorer()
    db = _get_db()
    try:
        query = db.query(Lead)
        if lead_id:
            query = query.filter(Lead.id == lead_id)

        leads = query.all()
        if not leads:
            console.print("[yellow]No leads found.[/yellow]")
            return

        updated = 0
        for lead in leads:
            lead_dict = {
                "county": lead.county,
                "source_type": lead.source_type,
                "parcel_apn": lead.parcel_apn,
                "excess_proceeds_amount": lead.excess_proceeds_amount,
                "excess_proceeds_signal": lead.excess_proceeds_signal,
                "likely_claimant_type": lead.likely_claimant_type,
                "likely_claimant_name": lead.likely_claimant_name,
                "sale_date": lead.sale_date,
            }
            result = scorer.score(lead_dict)
            lead.score = result.score
            lead.priority_rank = result.priority_rank
            lead.legal_risk_flag = result.legal_risk_flag
            lead.score_explanation = explanation_to_json(result.explanation)
            updated += 1

        db.commit()
        console.print(f"[green]Rescored {updated} lead(s).[/green]")
    finally:
        db.close()


@app.command()
def export(
    output: str = typer.Option("./data/exports/leads_export.csv", "--output", "-o"),
    county: Optional[str] = typer.Option(None, "--county", "-c"),
    min_score: Optional[float] = typer.Option(None, "--min-score"),
) -> None:
    """Export leads to CSV."""
    db = _get_db()
    try:
        query = db.query(Lead)
        if county:
            query = query.filter(Lead.county == county)
        if min_score is not None:
            query = query.filter(Lead.score >= min_score)
        query = query.order_by(Lead.priority_rank.asc(), Lead.score.desc())
        leads = query.all()

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            "id", "county", "source_type", "source_url", "parcel_apn", "situs_address",
            "sale_date", "excess_proceeds_amount", "likely_claimant_type", "likely_claimant_name",
            "score", "priority_rank", "legal_risk_flag", "review_status", "outreach_status",
            "notes", "last_checked_at", "created_at",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for lead in leads:
                writer.writerow({fld: getattr(lead, fld, "") or "" for fld in fields})

        console.print(f"[green]Exported {len(leads)} leads to {output_path}[/green]")
    finally:
        db.close()


@app.command()
def status() -> None:
    """Show system status: lead counts, last scrape runs."""
    db = _get_db()
    try:
        total = db.query(Lead).count()
        pending = db.query(Lead).filter(Lead.review_status == "pending").count()
        qualified = db.query(Lead).filter(Lead.review_status == "qualified").count()
        legal_review = db.query(Lead).filter(Lead.legal_risk_flag == "REQUIRES_LEGAL_REVIEW").count()

        table = Table(title="Proceeds Navigator — System Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Leads", str(total))
        table.add_row("Pending Review", str(pending))
        table.add_row("Qualified", str(qualified))
        table.add_row("Require Legal Review", f"[red]{legal_review}[/red]" if legal_review else "0")
        console.print(table)

        runs = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(8).all()
        if runs:
            run_table = Table(title="Recent Scrape Runs")
            run_table.add_column("County")
            run_table.add_column("Started")
            run_table.add_column("Found")
            run_table.add_column("New")
            run_table.add_column("Status")
            for r in runs:
                run_table.add_row(
                    r.county,
                    r.started_at.strftime("%Y-%m-%d %H:%M"),
                    str(r.leads_found),
                    str(r.leads_new),
                    f"[green]{r.status}[/green]" if r.status == "success" else f"[yellow]{r.status}[/yellow]",
                )
            console.print(run_table)
    finally:
        db.close()


@app.command()
def init() -> None:
    """Initialize the database (create tables)."""
    init_db()
    console.print("[green]Database initialized.[/green]")


if __name__ == "__main__":
    app()
