import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from groq import Groq

# -------------------
# Load environment
# -------------------
load_dotenv()

SUPABASE_DB_URL = st.secrets.get("SUPABASE_DB_URL") or os.getenv("SUPABASE_DB_URL")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GROQ_MODEL = st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile") or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not SUPABASE_DB_URL or not GROQ_API_KEY:
    st.error("❌ Missing SUPABASE_DB_URL or GROQ_API_KEY in environment.")
    st.stop()

# -------------------
# Setup
# -------------------
engine = create_engine(SUPABASE_DB_URL)
client = Groq(api_key=GROQ_API_KEY)

# Table schema for priming LLM
TABLE_SCHEMA = """
You are a PostgreSQL expert.
You must only query from table re_postsales.
Here are the columns and their types:
- customer_id (text, primary key)
- name (text)
- email (text)
- phone (text)
- property_id (text)
- region (text)
- property_type (text)
- purchase_date (text, should be cast to DATE when used in time analysis)
- maintenance_due (text)
- payment_status (text)
- maintenance_requests (bigint)
- satisfaction_score (double precision)
- utilities_consumption (double precision)
- referral_source (text)
- warranty_claims (boolean)
- insurance_status (text)

Rules:
- Use only these columns.
- If dates are required, cast text to DATE using TO_DATE(purchase_date,'DD-MM-YYYY').
- Return ONLY raw SQL with no markdown or explanation.
"""

# -------------------
# Helpers
# -------------------
def clean_sql(query: str) -> str:
    """Remove markdown fences and keep pure SQL and fix date casting"""
    query = query.strip()
    if query.startswith("```"):
        parts = query.split("```")
        if len(parts) >= 2:
            query = parts[1]
        query = query.replace("sql\n", "").replace("sql\r\n", "").strip()
    # Patch: fix date casting
    query = query.replace("CAST(purchase_date AS DATE)", "TO_DATE(purchase_date, 'DD-MM-YYYY')")
    return query.strip()

def ask_groq(prompt: str, system_msg: str = None) -> str:
    """Send a prompt to Groq"""
    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0,
    )
    return resp.choices[0].message.content.strip()

def detect_viz_type(user_prompt: str, llm_hint: str) -> str:
    """Decide visualization type based on user prompt + LLM suggestion"""
    text = f"{user_prompt.lower()} {llm_hint.lower()}"
    if any(word in text for word in ["trend", "over time", "line", "time-series"]):
        return "line"
    # Patch: move pie detection above histogram to prioritize proportions
    if any(word in text for word in ["pie", "proportion", "share", "percentage"]):
        return "pie"
    if any(word in text for word in ["distribution", "histogram", "frequency"]):
        return "hist"
    if any(word in text for word in ["scatter", "against", "x-axis", "y-axis", "relationship"]):
        return "scatter"
    if any(word in text for word in ["bar", "compare", "count", "group by"]):
        return "bar"
    return "table"

def plot_chart(df: pd.DataFrame, chart_type: str):
    """Render chart in Streamlit"""
    if chart_type == "bar" and len(df.columns) >= 2:
        st.bar_chart(df.set_index(df.columns[0]))
    elif chart_type == "line" and len(df.columns) >= 2:
        st.line_chart(df.set_index(df.columns[0]))
    elif chart_type == "pie" and len(df.columns) == 2:
        fig, ax = plt.subplots()
        df.set_index(df.columns[0]).plot.pie(
            y=df.columns[1], autopct='%1.1f%%', ax=ax, legend=False
        )
        st.pyplot(fig)
    elif chart_type == "scatter" and len(df.columns) >= 2:
        fig, ax = plt.subplots()
        ax.scatter(df[df.columns[0]], df[df.columns[1]])
        ax.set_xlabel(df.columns[0])
        ax.set_ylabel(df.columns[1])
        st.pyplot(fig)
    elif chart_type == "hist" and len(df.columns) >= 1:
        fig, ax = plt.subplots()
        df[df.columns[0]].hist(ax=ax, bins=10)
        ax.set_xlabel(df.columns[0])
        st.pyplot(fig)
    else:
        st.write("🤷 Showing raw data (no clear viz type).")
        st.dataframe(df)

# -------------------
# Streamlit UI
# -------------------
st.title("🔮 NL Prompt → BI Dashboard")

prompt = st.text_area("Enter your request:", "Show customer count by payment status")

if st.button("Run Query"):
    try:
        # Step 1: Optimise natural language prompt
        optimised_prompt = ask_groq(
            prompt,
            system_msg="Rewrite the user's BI request into a precise, short analytical task."
        )
        st.info(f"Optimised Prompt: {optimised_prompt}")

        # Step 2: Generate SQL with schema awareness
        sql_query = ask_groq(
            optimised_prompt,
            system_msg=TABLE_SCHEMA
        )
        sql_query = clean_sql(sql_query)
        st.code(sql_query, language="sql")

        # Step 3: Run SQL
        df = pd.read_sql_query(sql_query, engine)

        if df.empty:
            st.warning("⚠️ Query returned no results.")
        else:
            st.subheader("📊 Data Preview")
            st.dataframe(df)

            # Step 4: Detect viz type
            viz_type = detect_viz_type(prompt, optimised_prompt)
            st.subheader(f"📊 Visualization ({viz_type})")
            plot_chart(df, viz_type)

    except Exception as e:
        st.error(f"❌ Error: {e}")

