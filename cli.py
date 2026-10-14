"""
Production Command Line Interface for FreightGuard AI Shipping Cost Assistant.
"""

import os
import sys
import argparse
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from freight_guard.core.pipeline import ShippingCostPipeline
from freight_guard.eval.harness import EvaluationHarness
from freight_guard.eval.reproducibility import ReproducibilityVerifier
from freight_guard.eval.cost_logger import CostLogger
from freight_guard.assistant.qa_agent import ShippingCostQAAgent


console = Console()

DEFAULT_SHIPMENT_CSV = "data/shipment_records.csv"
DEFAULT_NOTES_CSV = "data/context_notes.csv"
DEFAULT_SAMPLE_CSV = "data/sample_output_format_v2.csv"
DEFAULT_OUTPUT_CSV = "output.csv"


def cmd_run(args):
    """Executes the pipeline and exports contract output CSV."""
    console.print(Panel.fit("[bold cyan]FreightGuard AI[/bold cyan]: Running Shipping Cost Anomaly Detection...", border_style="cyan"))
    
    pipeline = ShippingCostPipeline(
        shipment_csv_path=args.shipments,
        context_notes_csv_path=args.notes,
        hist_threshold_pct=args.hist_thresh,
        peer_threshold_pct=args.peer_thresh
    )

    out_df = pipeline.export_submission_csv(args.output, include_all_weeks=args.all_weeks)
    
    table = Table(title="Top Anomaly Candidates Evaluated", show_header=True, header_style="bold magenta")
    table.add_column("Route", style="dim", width=18)
    table.add_column("Week", width=12)
    table.add_column("Cost/T-km", justify="right", width=10)
    table.add_column("vs History", justify="right", width=16)
    table.add_column("vs Peers", justify="right", width=16)
    table.add_column("Flagged", justify="center", width=15)
    table.add_column("Note ID", justify="center", width=8)

    for _, r in out_df.head(10).iterrows():
        status_style = "green" if "justified" in str(r['flagged']).lower() else ("red" if str(r['flagged']) == "Yes" else "white")
        table.add_row(
            str(r['route']),
            str(r['week_of']),
            f"₹{r['cost_per_tonne_km']:.2f}",
            str(r['vs_own_history']).split(" vs")[0],
            str(r['vs_similar_routes']).split(" vs")[0],
            f"[{status_style}]{r['flagged']}[/{status_style}]",
            str(r['matched_note_id']) if r['matched_note_id'] else "-"
        )

    console.print(table)
    console.print(f"[bold green]✔ Successfully exported contract-compliant CSV to:[/bold green] [yellow]{args.output}[/yellow] ({len(out_df)} rows)\n")


def cmd_eval(args):
    """Runs the evaluation harness and adversarial probe tests."""
    console.print(Panel.fit("[bold green]FreightGuard AI[/bold green]: Running Evaluation Benchmark & Guardrail Probes...", border_style="green"))
    pipeline = ShippingCostPipeline(args.shipments, args.notes)
    harness = EvaluationHarness(pipeline)

    bench = harness.run_guardrail_stress_tests()
    
    table = Table(title="Adversarial Probe Suite (Valid Justifications + Distractor Traps)", show_header=True, header_style="bold blue")
    table.add_column("Probe ID", width=22)
    table.add_column("Description", width=40)
    table.add_column("Expected", width=12)
    table.add_column("Actual", width=12)
    table.add_column("Result", justify="center", width=10)

    for p in bench["probe_details"]:
        res_str = "[bold green]PASS[/bold green]" if p["passed"] else "[bold red]FAIL[/bold red]"
        exp_str = f"Valid ({p['expected_note_id']})" if p["expected_valid"] else "Rejected"
        act_str = f"Valid ({p['actual_note_id']})" if p["actual_valid"] else "Rejected"
        table.add_row(p["probe_id"], p["description"], exp_str, act_str, res_str)

    console.print(table)
    console.print(f"\n[bold]Overall Benchmark Score:[/bold] [cyan]{bench['score_pct']:.1f}%[/cyan] ({bench['passed_probes']}/{bench['total_probes']} passed)")
    console.print(f"[bold]Measured Hallucination Rate:[/bold] [green]{bench['hallucination_rate_pct']:.1f}%[/green]")

    sample_contract = harness.verify_sample_format_contract(args.sample)
    console.print(f"[bold]Sample Output Contract Fidelity:[/bold] {'[bold green]100% MATCH (PASS)[/bold green]' if sample_contract['all_sample_passed'] else '[bold red]FAIL[/bold red]'}\n")


def cmd_reproduce(args):
    """Runs 3 untouched passes and exports reproducibility_report.md."""
    console.print(Panel.fit("[bold yellow]FreightGuard AI[/bold yellow]: Running 3 Untouched Sequential Passes...", border_style="yellow"))
    verifier = ReproducibilityVerifier(args.shipments, args.notes)
    results = verifier.run_three_passes()

    report_md = verifier.generate_markdown_report(results)
    out_file = "reproducibility_report.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    console.print(f"[bold green]✔ Reproducibility verified:[/bold green] All 3 runs identical: [bold cyan]{results['all_runs_identical']}[/bold cyan]")
    console.print(f"  SHA-256 Checksum: [dim]{results['run_hashes']['run_1_sha256']}[/dim]")
    console.print(f"[bold green]✔ Saved audit report to:[/bold green] [yellow]{out_file}[/yellow]\n")


def cmd_cost(args):
    """Generates token and cost accounting report."""
    console.print(Panel.fit("[bold magenta]FreightGuard AI[/bold magenta]: Calculating Token Usage & Execution Cost...", border_style="magenta"))
    pipeline = ShippingCostPipeline(args.shipments, args.notes)
    df = pipeline.run(include_all_weeks=False)

    logger = CostLogger(df)
    report_md = logger.generate_markdown_report()
    out_file = "token_cost_log.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    stats = logger.calculate_token_stats()
    console.print(f"[bold green]✔ Total Tokens Screened:[/bold green] {stats['total_tokens']:,} (Input: {stats['total_input_tokens']:,}, Output: {stats['total_output_tokens']:,})")
    console.print(f"[bold green]✔ Default Execution Cost (Local ONNX):[/bold green] [bold cyan]$0.000000 (Free)[/bold cyan]")
    console.print(f"[bold green]✔ Saved cost audit log to:[/bold green] [yellow]{out_file}[/yellow]\n")


def cmd_ask(args):
    """Interactive natural language Q&A assistant."""
    query = " ".join(args.question)
    console.print(Panel.fit(f"[bold cyan]Query:[/bold cyan] {query}", border_style="cyan"))

    pipeline = ShippingCostPipeline(args.shipments, args.notes)
    agent = ShippingCostQAAgent(pipeline)
    response = agent.answer_query(query)

    console.print("\n[bold green]Assistant Answer:[/bold green]")
    console.print(response["answer"])
    console.print()


def cmd_serve(args):
    """Starts the executive web dashboard server."""
    import uvicorn
    console.print(Panel.fit(f"[bold green]FreightGuard AI Web Dashboard[/bold green]\nStarting web server on http://localhost:{args.port} ...", border_style="green"))
    from freight_guard.app.server import create_app
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=args.port)


def main():
    parser = argparse.ArgumentParser(description="FreightGuard AI - Shipping Cost Anomaly Detection & Assistant")
    parser.add_argument("--shipments", default=DEFAULT_SHIPMENT_CSV, help="Path to shipment_records.csv")
    parser.add_argument("--notes", default=DEFAULT_NOTES_CSV, help="Path to context_notes.csv")
    parser.add_argument("--sample", default=DEFAULT_SAMPLE_CSV, help="Path to sample_output_format_v2.csv")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    p_run = subparsers.add_parser("run", help="Run detection and export submission CSV")
    p_run.add_argument("--output", default=DEFAULT_OUTPUT_CSV, help="Output CSV path")
    p_run.add_argument("--all-weeks", action="store_true", help="Include all 728 route-weeks in output")
    p_run.add_argument("--hist-thresh", type=float, default=8.0, help="Hist threshold % (default: 8.0)")
    p_run.add_argument("--peer-thresh", type=float, default=20.0, help="Peer threshold % (default: 20.0)")
    p_run.set_defaults(func=cmd_run)

    # eval command
    p_eval = subparsers.add_parser("eval", help="Run guardrail stress tests and benchmark")
    p_eval.set_defaults(func=cmd_eval)

    # reproduce command
    p_rep = subparsers.add_parser("reproduce", help="Run 3-pass reproducibility verification")
    p_rep.set_defaults(func=cmd_reproduce)

    # cost command
    p_cost = subparsers.add_parser("cost", help="Generate token and cost audit log")
    p_cost.set_defaults(func=cmd_cost)

    # ask command
    p_ask = subparsers.add_parser("ask", help="Ask questions about findings in plain English")
    p_ask.add_argument("question", nargs="+", help="Natural language question")
    p_ask.set_defaults(func=cmd_ask)

    # serve command
    p_serve = subparsers.add_parser("serve", help="Launch interactive web dashboard")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
