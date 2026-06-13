# CGPSC Reader

An AI-assisted pipeline for extracting, validating, analyzing, and storing CGPSC (Chhattisgarh Public Service Commission) examination papers.

## Project Goal

Transform raw CGPSC PDF question papers into a structured intelligence database for:

* Topic frequency analysis
* Historical trend analysis
* Question pattern discovery
* Prediction engine development
* Mock test generation
* CGPSC preparation support

---

## Pipeline Architecture

```text
PDF
 ↓
OCR
 ↓
Parser
 ↓
Validator
 ↓
Analyzer
 ↓
Analyzer Validator
 ↓
Statistics
 ↓
Database Ingest
```

---

## Current Status

| Component        | Status               |
| ---------------- | -------------------- |
| OCR              | ✅ Working            |
| Parser           | 🔧 Under Improvement |
| Validator        | ✅ Working            |
| Analyzer         | ✅ Working            |
| Statistics       | ✅ Working            |
| Database Ingest  | ✅ Working            |
| Batch Processing | ✅ Working            |

---

## Repository Structure

```text
reader/
│
├── src/
│   ├── pipeline.py
│   ├── process_all.py
│   ├── parser.py
│   ├── validator.py
│   ├── analyzer.py
│   ├── validate_analyzer.py
│   ├── ingest.py
│   └── config.py
│
├── data/
│   ├── pdfs/
│   ├── years/
│   ├── json/
│   ├── analyzed/
│   └── validation/
│
├── database/
│   ├── questions/
│   ├── metadata/
│   ├── stats/
│   └── index.json
│
└── README.md
```

---

## Usage

### Process a Single Year

```bash
python src/pipeline.py 2025
```

### Process Specific Stages

```bash
python src/pipeline.py 2025 --steps parser validator
```

### Skip OCR

```bash
python src/pipeline.py 2025 --skip-ocr
```

### Batch Process All Papers

```bash
python src/process_all.py
```

---

## Database Output

After successful ingestion:

```text
database/
├── questions/
├── metadata/
├── stats/
└── index.json
```

The database becomes the foundation for future CGPSC analytics and intelligence systems.

---

## Future Roadmap

### Phase 1 — Stable Extraction

* Improve parser accuracy
* Validate all historical papers
* Achieve 100% question extraction

### Phase 2 — Analytics

* Subject frequency analysis
* Topic trend analysis
* PYQ clustering
* Difficulty estimation

### Phase 3 — Intelligence Layer

* Question prediction engine
* Smart revision planner
* Personalized weak-area tracking
* AI-generated mock tests

---

## Author

Built as a long-term CGPSC Intelligence System project combining OCR, NLP, analytics, and AI-assisted examination research.
