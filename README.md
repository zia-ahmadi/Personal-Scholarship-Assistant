# Personal Opportunity Analyzer

A small local assistant for checking whether scholarships, fellowships, internships, and other opportunities are suitable for a personal student profile.

V1 is intentionally simple and free:

- Streamlit for the interface
- Requests and BeautifulSoup for webpage text extraction
- Ollama for local AI analysis
- Python rules for matching opportunities against `profile.yaml`

## Current Status

This first step creates the minimal project structure and a starter Streamlit app. Webpage extraction, Ollama analysis, structured JSON output, and matching will be added step by step.

## Setup on Ubuntu

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Project Structure

```text
.
├── app.py
├── profile.yaml
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── scraper.py
│   ├── analyzer.py
│   ├── matcher.py
│   └── models.py
└── data/
    └── opportunities/
```

