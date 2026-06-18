"""Initialize pipeline tracker with existing migrated files."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.pipeline_tracker import init_pipeline_db, upsert_page

PDF_NAME = "1952_1_100_2.pdf"
PDF_PATH = Path(f"C:/Users/adity/Desktop/ocr_devnagri/ceDscX/{PDF_NAME}")
IMAGES_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_images/1952_1_100_2")
OCR_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
PIPELINE_DB = Path("C:/Users/adity/Desktop/ocr_devnagri/data/pipeline.db")

init_pipeline_db(PIPELINE_DB)

image_files = sorted(IMAGES_DIR.glob("1952_1_100_2_page_*.png"))
for img_path in image_files:
    page_index = int(img_path.stem.split('_page_')[1])
    txt_path = OCR_DIR / f"1952_1_100_2_page_{page_index:03d}.txt"
    has_txt = txt_path.exists()
    upsert_page(
        pdf_name=PDF_NAME,
        pdf_path=str(PDF_PATH),
        page_number=page_index,
        image_path=str(img_path),
        ocr_text_path=str(txt_path) if has_txt else None,
        ocr_status="done" if has_txt else "pending",
        db_path=PIPELINE_DB,
    )

print(f"Initialized tracker with {len(image_files)} page records.")
