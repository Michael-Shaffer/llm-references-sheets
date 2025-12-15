import argparse
import sys
import logging
from pathlib import Path

# Google Standard: Use relative imports within the package.
# This assumes the script is run as a module (e.g. `python -m src.core.ingestion.cli`)
try:
    from .factory import ProcessorFactory
    # Trigger registration by importing the processors package
    from . import processors
except ImportError as e:
    # Helpful error if the user tries to run this file directly with `python cli.py`
    print("Error: This script must be run as a module from the project root.", file=sys.stderr)
    print("Usage: python -m src.core.ingestion.cli [args]", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_args(data_path: Path, mode: str) -> None:
    """Validates command-line arguments and paths."""
    if not data_path.exists():
        raise FileNotFoundError(f"Input file not found: {data_path}")
        
    if mode in ["IETP", "Reference_Card"] and data_path.suffix.lower() != ".pdf":
        raise ValueError(f"For --mode {mode} the input file must have a .pdf extension. Received {data_path.suffix}")

def parse_args() -> argparse.Namespace:
    """
    Parses command-line argument for the ingestion script.
    """
    ap = argparse.ArgumentParser(description="Ingestion CLI")

    # Get available processors dynamically from the factory/registry
    available_modes = ProcessorFactory.available_processors()
    
    if not available_modes:
        # Warn if no processors were found - this usually implies an import/discovery issue
        logger.warning("No processors registered. Ensure 'src.core.ingestion.processors' contains valid processor modules.")

    ap.add_argument(
        "--data",
        required=True,
        help="Path to input file."
    )

    ap.add_argument(
        "--mode",
        required=True,
        choices=available_modes if available_modes else [], 
        help=f"Category of input file. Available: {available_modes}"
    )

    ap.add_argument(
        "--pages",
        help="The range of pages to process, specified as 'start-end' (e.g., --pages 1-4). \
                Note that start is inclusive and end is exclusive.",
        type=str
    )

    return ap.parse_args()

def run_ingestion(args: argparse.Namespace) -> None:
    data_path = Path(args.data)
    mode = args.mode

    start_page, end_page = None, None
    if args.pages:
        try:
            start_page, end_page = map(int, args.pages.split("-"))
        except ValueError:
            raise ValueError("Invalid format for --pages. Use the format 'start-end' (e.g., --pages 1-4)")

    validate_args(data_path, mode)

    logger.info(f"Starting ingestion for {mode} document: {data_path}")
    
    try:
        processor = ProcessorFactory.get_processor(mode)
        
        # Pass pages if available
        kwargs = {}
        if start_page is not None and end_page is not None:
             kwargs['page_nums'] = (start_page, end_page)
             
        result = processor.parse(data_path, **kwargs)
        logger.info(f"Ingestion complete. Result: {result}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)

def main() -> None:
    # args parsing happens inside main to allow for easier testing or importing of main
    args = parse_args()
    try:
        run_ingestion(args)
    except Exception as e:
        logger.error(f"CLI Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
