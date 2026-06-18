import sys
sys.path.insert(0, '.')
from src.database.pipeline_tracker import get_pdf_progress

p = get_pdf_progress('1952_1_100_2.pdf', 'data/pipeline.db')
for k, v in p.items():
    print(f'{k}: {v}')
