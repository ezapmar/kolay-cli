"""RAG command group for Kolay CLI."""
import time
import typer
from rich.console import Console

app = typer.Typer(help="Manage Kolay RAG Corporate Memory.")
console = Console(highlight=False)

@app.command(name="ingest")
def ingest(
    tenant_id: str = typer.Argument(..., help="Tenant namespace to inject the document into."),
    file_path: str = typer.Argument(..., help="Path to the PDF file to ingest."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Ingest a corporate policy PDF into the Vector Database."""
    import os
    if not os.path.isfile(file_path):
        console.print(f"[red]Error: File {file_path} not found.[/red]")
        raise typer.Exit(1)
        
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to ingest '{os.path.basename(file_path)}' into namespace '{tenant_id}'?")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)
            
    try:
        from ..rag.pipeline import process_file_to_qdrant
    except ImportError as exc:
        console.print(f"[red]RAG dependencies missing: {exc}. Run: uv pip install -e \".[rag]\"[/red]")
        raise typer.Exit(1)
        
    with console.status(f"[cyan]Parsing and chunking PDF into tenant {tenant_id}...[/cyan]"):
        t0 = time.monotonic()
        try:
            num_chunks = process_file_to_qdrant(tenant_id, file_path)
        except Exception as exc:
            console.print(f"[red]Ingestion failed: {exc}[/red]")
            raise typer.Exit(1)
        elapsed = time.monotonic() - t0
        
    console.print(f"[bold green]Success![/bold green] Ingested {num_chunks} vector chunks into '{tenant_id}' in {elapsed:.1f}s.")
