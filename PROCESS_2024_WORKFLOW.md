# 2024 CGPSC Paper Processing - Workflow Execution

## Pipeline Overview

The complete workflow to process `data/pdfs/cgpsc_2024.pdf`:

```
PDF → PDF-to-Images → OCR → Parser → Analyzer → Statistics → Database Ingest
```

---

## Step-by-Step Commands

### **Step 1: PDF to Images**

Convert the PDF to images (required for OCR):

```bash
python -c "
from pathlib import Path
from src.pdf_to_images import pdf_to_images

pdf_path = 'data/pdfs/cgpsc_2024.pdf'
output_dir = 'data/images_2024'

images = pdf_to_images(pdf_path, output_dir)
print(f'Generated {len(images)} images from {pdf_path}')
for img in images:
    print(f'  - {img}')
"
```

**Expected Output:**
```
data/images_2024/page_001.png
data/images_2024/page_002.png
...
data/images_2024/page_NNN.png
```

---

### **Step 2: OCR (Extract Text)**

Process images and extract text using Tesseract:

```bash
python -c "
from pathlib import Path
from src.ocr import image_to_text
from src.clean_text import clean_text

# Get all images
image_dir = Path('data/images_2024')
images = sorted(image_dir.glob('page_*.png'))

full_text = ''
for i, image_path in enumerate(images, 1):
    print(f'OCR: {image_path}')
    text = image_to_text(str(image_path))
    full_text += text + '\n\n'

# Clean after OCR
full_text = clean_text(full_text)

# Save
Path('data/raw_text').mkdir(parents=True, exist_ok=True)
with open('data/raw_text/ocr_output_2024.txt', 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f'Saved cleaned OCR text: data/raw_text/ocr_output_2024.txt')
"
```

**Expected Output:**
```
data/raw_text/ocr_output_2024.txt (cleaned OCR text)
```

---

### **Step 3: Parse Questions**

Extract structured questions from OCR text:

```bash
python src/parser.py data/raw_text/ocr_output_2024.txt \
  -o data/json/questions_draft_2024.json
```

**Expected Output:**
```json
{
  "source_file": "data/raw_text/ocr_output_2024.txt",
  "exam": "CGPSC Prelims",
  "year": 2025,
  "draft": true,
  "summary": {
    "questions_extracted": 100,
    "expected_questions": 100,
    "questions_with_four_options": 95,
    "questions_flagged_for_review": 5
  },
  "questions": [...]
}
```

**File:** `data/json/questions_draft_2024.json`

---

### **Step 4: Validate Questions**

Check that extraction produced expected output:

```bash
python src/validator.py data/json/questions_draft_2024.json
```

**Expected Output:**
```json
{
  "valid": true,
  "questions_count": 100,
  "warnings": 5
}
```

---

### **Step 5: Run Analyzer**

Classify questions with taxonomy:

```bash
python src/analyzer.py data/json/questions_draft_2024.json \
  -t data/taxonomy/cgpsc_taxonomy_v1.json \
  -o data/analyzed/cgpsc_2024_analyzed.json
```

**Expected Output:**
```json
{
  "schema_version": "analyzer-record-v1",
  "taxonomy_version": "cgpsc-taxonomy-v1.0.0",
  "exam": "CGPSC Prelims",
  "year": 2024,
  "summary": {
    "questions": 100,
    "subjects": {...},
    "topics": {...},
    "difficulty": {...}
  },
  "questions": [...]
}
```

**File:** `data/analyzed/cgpsc_2024_analyzed.json`

---

### **Step 6: Validate Analyzer Output**

Verify analyzer produced valid records:

```bash
python src/validate_analyzer.py data/analyzed/cgpsc_2024_analyzed.json
```

**Expected Output:**
```json
{
  "valid": true,
  "questions": 100
}
```

---

### **Step 7: Generate Statistics**

Create statistics report for the paper:

```bash
python -c "
from pathlib import Path
from src.statistics import StatisticsGenerator

generator = StatisticsGenerator(
    input_file='data/analyzed/cgpsc_2024_analyzed.json',
    output_dir='data/stats'
)

generator.load_questions()
generator.generate_statistics()

# Validate
errors = generator.validate_counts()
if errors:
    print('Validation errors:')
    for error in errors:
        print(f'  - {error}')
else:
    print('✓ All validation checks passed')

# Save
output_path = generator.save_report('cgpsc_2024_stats.json')
print(f'Statistics saved: {output_path}')

# Show summary
generator.print_summary()
"
```

**Expected Output:**
```
data/stats/cgpsc_2024_stats.json

Total Questions: 100
  
=== SUBJECTS ===
chhattisgarh_studies    34
history                 11
polity_governance       11
...
```

---

### **Step 8: Ingest into Database**

Store the 2024 paper in the database:

```bash
python src/ingest.py data/analyzed/cgpsc_2024_analyzed.json 2024
```

**Expected Output:**
```
======================================================================
CGPSC PAPER INGESTION WORKFLOW
======================================================================

Step 1: Validating input file...
  Valid analyzer record for 2024 (100 questions)

Step 2: Ingesting paper into database...
  ✓ Paper for 2024 ingested successfully (100 questions)

Step 3: Generating statistics...
  Statistics generated: database/stats/cgpsc_2024_stats.json

Step 4: Database status...
  CGPSC INTELLIGENCE DATABASE STATUS
  Total Papers: 2
  
  Year     Exam                 Questions    Ingested
  2024     CGPSC Prelims        100          2026-06-12
  2025     CGPSC Prelims        100          2026-06-12
  
  Total Questions Across All Papers: 200

======================================================================
✓ WORKFLOW COMPLETED SUCCESSFULLY
======================================================================
```

---

## Verification Checklist

After completing all steps, verify:

**OCR & Parsing:**
- [ ] `data/images_2024/` contains PNG images
- [ ] `data/raw_text/ocr_output_2024.txt` exists
- [ ] `data/json/questions_draft_2024.json` has 100 questions

**Analysis:**
- [ ] `data/analyzed/cgpsc_2024_analyzed.json` exists
- [ ] Schema version = `analyzer-record-v1`
- [ ] Year field = `2024`
- [ ] Contains 100 questions with aggregation dict

**Statistics:**
- [ ] `data/stats/cgpsc_2024_stats.json` exists
- [ ] Subject counts sum to 100
- [ ] Topic counts sum to 100
- [ ] Difficulty counts sum to 100

**Database:**
- [ ] `database/questions/2024.json` exists
- [ ] `database/metadata/2024_metadata.json` exists
- [ ] `database/stats/cgpsc_2024_stats.json` exists
- [ ] `database/index.json` updated with 2024 entry
- [ ] `database/print_database_status()` shows 2 papers (2024, 2025)

**Total Questions:**
- [ ] `database/questions/2024.json`: 100 questions
- [ ] `database/questions/2025.json`: 100 questions
- [ ] Combined total: 200 questions

---

## Debugging

### If PDF to Images fails:
```bash
# Check PDF exists
ls -la data/pdfs/cgpsc_2024.pdf

# Check pypdf library
python -c "import pypdf; print(pypdf.__version__)"
```

### If OCR fails:
```bash
# Check Tesseract installation
where tesseract
# or
which tesseract

# Verify image file
file data/images_2024/page_001.png
```

### If Parser fails:
```bash
# Check OCR text exists
wc -l data/raw_text/ocr_output_2024.txt

# Validate JSON output
python -m json.tool data/json/questions_draft_2024.json | head -50
```

### If Analyzer fails:
```bash
# Validate input JSON
python -c "import json; json.load(open('data/json/questions_draft_2024.json'))"

# Check taxonomy exists
ls -la data/taxonomy/cgpsc_taxonomy_v1.json
```

### If Statistics fails:
```bash
# Check aggregation dict in questions
python -c "
import json
data = json.load(open('data/analyzed/cgpsc_2024_analyzed.json'))
q = data['questions'][0]
print(json.dumps(q.get('aggregation'), indent=2))
"
```

### If Database Ingest fails:
```bash
# Check database initialized
python -c "from src.database import PaperDatabase; db = PaperDatabase(); db.print_database_status()"

# Verify 2025 exists
ls -la database/questions/
```

---

## Quick Execution (Copy-Paste)

To run the complete workflow:

```bash
# Step 1-2: PDF → Images → OCR
python -c "
from pathlib import Path
from src.pdf_to_images import pdf_to_images
from src.ocr import image_to_text
from src.clean_text import clean_text

images = pdf_to_images('data/pdfs/cgpsc_2024.pdf', 'data/images_2024')
full_text = ''
for img in images:
    full_text += image_to_text(img) + '\n\n'
full_text = clean_text(full_text)
Path('data/raw_text').mkdir(parents=True, exist_ok=True)
Path('data/raw_text/ocr_output_2024.txt').write_text(full_text, encoding='utf-8')
print('✓ OCR complete')
"

# Step 3-4: Parse & Validate
python src/parser.py data/raw_text/ocr_output_2024.txt -o data/json/questions_draft_2024.json
python src/validator.py data/json/questions_draft_2024.json

# Step 5-6: Analyze & Validate
python src/analyzer.py data/json/questions_draft_2024.json \
  -t data/taxonomy/cgpsc_taxonomy_v1.json \
  -o data/analyzed/cgpsc_2024_analyzed.json
python src/validate_analyzer.py data/analyzed/cgpsc_2024_analyzed.json

# Step 7-8: Statistics & Ingest
python src/ingest.py data/analyzed/cgpsc_2024_analyzed.json 2024

# Verify
python -c "from src.database import PaperDatabase; PaperDatabase().print_database_status()"
```

---

## Expected Final State

```
database/
├── questions/
│   ├── 2024.json ✓
│   └── 2025.json ✓
├── metadata/
│   ├── 2024_metadata.json ✓
│   └── 2025_metadata.json ✓
├── stats/
│   ├── cgpsc_2024_stats.json ✓
│   └── cgpsc_2025_stats.json ✓
└── index.json ✓

Total Questions in Database: 200
Status: Ready for trend analysis
```

---

## Notes

- Each step is independent and can be re-run
- Use `--overwrite` flag in ingest if reprocessing
- Statistics are auto-generated during ingest
- Year must match in JSON, Analyzer, and Ingest step
- All outputs use `2024` in filenames (not `2025`)
