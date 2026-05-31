"""
Main entry point for the RAG system.
"""
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.rag import RAGPipeline
from src.utils import ensure_directories, setup_logging

console = Console()


def main():
    """Main function to run the RAG system."""
    # Setup
    ensure_directories()
    logger = setup_logging()

    console.print(Panel.fit(
        "[bold green]🤖 Local AI RAG System[/bold green]\n"
        "[dim]Powered by Qwen 2.5 + ChromaDB[/dim]",
        border_style="green"
    ))

    # Initialize RAG
    console.print("\n[yellow]Đang khởi tạo hệ thống...[/yellow]")
    rag = RAGPipeline()

    # Show stats
    stats = rag.get_stats()
    console.print("\n[cyan]📊 Thông tin hệ thống:[/cyan]")
    console.print(f"   • LLM Model: {stats['llm_model']}")
    console.print(f"   • Embedding Model: {stats['embedding_model']}")
    console.print(f"   • Vector Store: {stats['vector_store']['name']} ({stats['vector_store']['count']} documents)")

    console.print("\n[green]✓ Hệ thống sẵn sàng![/green]")
    console.print("[dim]Gõ 'quit' hoặc 'exit' để thoát. Gõ 'load' để tải tài liệu.[/dim]\n")

    # Chat loop
    while True:
        try:
            question = Prompt.ask("\n[bold blue]Bạn[/bold blue]")

            if question.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]👋 Tạm biệt![/yellow]")
                break

            if question.lower() == "load":
                path = Prompt.ask("Nhập đường dẫn thư mục chứa tài liệu")
                count = rag.load_documents(path)
                console.print(f"[green]✓ Đã tải {count} document chunks[/green]")
                continue

            if question.lower() == "stats":
                stats = rag.get_stats()
                console.print(f"[cyan]📊 Documents: {stats['vector_store']['count']}[/cyan]")
                continue

            if not question.strip():
                continue

            # Query
            console.print("\n[dim]Đang xử lý...[/dim]")
            result = rag.query(question)

            # Display answer
            console.print("\n[bold green]🤖 AI:[/bold green]")
            console.print(Panel(result["answer"], border_style="green"))

            # Show sources count
            if result["sources"]:
                console.print(f"[dim]📚 Tham khảo từ {len(result['sources'])} nguồn[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Tạm biệt![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Lỗi: {e}[/red]")
            logger.exception("Error in main loop")


if __name__ == "__main__":
    main()
