# Text-to-SQL AI Assistant 🚀

A smart and conversational **Text-to-SQL (NL2SQL)** engine built with **Google Gemini 2.5 Flash** and Python. This application allows users to ask natural language questions (Turkish/English), which are dynamically translated into SQLite `SELECT` queries that execute in real time.

## ✨ Features
- **Conversational Memory (Chat state)**: Remembers the context from previous interactions! If you ask "How many cheap products are there?" followed by "What are their names?", it understands the flow seamlessly.
- **Schema-Aware Generation**: Automatically extracts and reads your SQLite table structures to craft highly accurate JOINs and subqueries.
- **Security-First**: Integrated safety measures to prevent accidental data loss. It only permits strictly `SELECT` (read-only) operations and prevents `DROP`, `DELETE`, `UPDATE`, etc.
- **Lightweight**: Uses `google-genai` SDK and completely runs in your terminal.

## ⚙️ Installation & Usage

### 1. Clone the project
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd sql-text
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root of the project and add your API key for Google Gemini:
```ini
GEMINI_API_KEY=your_api_key_here
```
*(Note: `.env` is strongly git-ignored to keep your keys safe!)*

### 4. Run the App
```bash
python3 main.py
```
*Currently configured to query the famous sample `Chinook_Sqlite.sqlite` music store database. To use your own database, simply modify the `DB_FILE` variable in `main.py`.*
