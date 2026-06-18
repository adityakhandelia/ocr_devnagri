"""PDF to image conversion utility.

This module provides functions to convert PDF pages to high-resolution PNG images
suitable for OCR processing.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Union

# Suppress PyMuPDF import warning for type checking
try:
    import fitz
except ImportError:
    fitz = None


def convert_pdf_to_images(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path],
    dpi: int = 300,
    prefix: str = "",
) -> List[str]:
    """Convert PDF pages to high-resolution PNG images.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save the output images.
        dpi: Resolution in dots per inch (default: 300).
        prefix: Optional prefix for output filenames.

    Returns:
        List of absolute paths to the saved image files.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If dpi is not a positive integer.
    """
    pdf_path_obj = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
    output_dir_obj = Path(output_dir) if isinstance(output_dir, str) else output_dir

    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path_obj}")

    if dpi <= 0:
        raise ValueError("DPI must be a positive integer")

    # Create output directory if it doesn't exist
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    # Convert to absolute path for consistency
    output_dir_obj = output_dir_obj.resolve()

    # Open the PDF
    doc = fitz.open(str(pdf_path_obj))
    saved_paths: List[str] = []

    # Calculate zoom factor for desired DPI
    # PDF default is 72 DPI, so zoom = desired_dpi / 72
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    # Generate base filename
    base_name = prefix if prefix else pdf_path_obj.stem

    # Process each page
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=matrix)

        # Generate output filename
        filename = f"{base_name}_page_{page_num + 1:03d}.png"
        file_path = output_dir_obj / filename

        # Save the image
        pix.save(str(file_path))
        # Save as absolute path string
        saved_paths.append(str(file_path.resolve()))

    doc.close()

    return saved_paths


def batch_convert_pdfs(
    pdf_dir: Union[str, Path], output_dir: Union[str, Path], dpi: int = 300
) -> Dict[str, List[str]]:
    """Convert all PDFs in a directory to images.

    Args:
        pdf_dir: Directory containing PDF files.
        output_dir: Directory to save the output images.
        dpi: Resolution in dots per inch (default: 300).

    Returns:
        Dictionary mapping PDF filenames to lists of image paths.
    """
    pdf_dir_obj = Path(pdf_dir) if isinstance(pdf_dir, str) else pdf_dir
    output_dir_obj = Path(output_dir) if isinstance(output_dir, str) else output_dir

    results: Dict[str, List[str]] = {}

    # Find all PDF files
    pdf_files = list(pdf_dir_obj.glob("*.pdf"))

    for pdf_file in pdf_files:
        try:
            image_paths = convert_pdf_to_images(
                pdf_file, output_dir_obj, dpi=dpi, prefix=pdf_file.stem
            )
            results[pdf_file.name] = image_paths
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            results[pdf_file.name] = []

    return results
