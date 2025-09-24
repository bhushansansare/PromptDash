# NL → BI Dashlet (Groq Llama + Supabase + Streamlit)

Prototype that converts natural language BI prompts into SQL + visualization using:
- Groq Llama (chat API)
- Supabase/Postgres (via SQLAlchemy)
- sqlglot for SQL AST validation
- Streamlit + Altair for UI and plots

## Security note (IMPORTANT)
You posted credentials publicly while requesting this. **Rotate your Supabase DB credentials and Groq API key immediately.** Use a read-only DB role for this app. Never commit secrets into git.

## Setup

1. Clone repo
2. Create a Python virtual env and install:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. Environment variables (recommended):
- `SUPABASE_DB_URL` : your Postgres connection URI (postgresql://user:pass@host:port/dbname)
- `GROQ_API_KEY` : your Groq API key
- `GROQ_MODEL` : e.g. `llama-3.3-70b-versatile` (optional)
- `GROQ_BASE` : optional override (defaults to https://api.groq.com/openai/v1)
- `MAX_ROWS` : optional

Example (Unix):
export SUPABASE_DB_URL="postgresql://postgres:...@aws-1-ap-south-1.pooler.supabase.com
:5432/postgres"
export GROQ_API_KEY="gsk_e2VmIyQJ5Sakcf0RLmdEWGdy..."
export GROQ_MODEL="llama-3.3-70b-versatile"


4. Start:
streamlit run app.py


## How it works
- User types NL prompt.
- App builds a conversation prompt with schema + examples, calls Groq chat completions endpoint.
- Model returns a JSON with `sql`, `params`, `visualization`, `explanation`.
- App validates SQL (sqlglot) ensuring only SELECTs and uses only allowed tables.
- SQL executed read-only; results rendered using Altair into three containers.

## Customization
- Edit `schema.json` to reflect your production schema or expand table/column allowlist.
- Add more high-quality `examples.json` few-shots to reduce hallucination.
- For production, implement:
- A true read-only DB role
- Query cost / timeouts and queueing
- Audit logging of prompts and final SQL
- Human-in-loop review for new queries

## Troubleshooting
- If Groq API returns a different JSON shape, inspect raw response printed to streamlit logs. Adjust `call_groq_chat` parsing accordingly.
- If SQL fails safety checks, the app will show an error; refine prompt or expand `schema.json`.

## Notes about Groq:
- This app calls Groq's OpenAI-compatible chat endpoint: `POST ${GROQ_BASE}/chat/completions`. If your Groq account uses a different endpoint, set `GROQ_BASE`.