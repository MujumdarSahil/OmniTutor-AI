# =============================================================================
# streamlit_app.py — OmniTutor AI: Ask (question + output) & Dashboard
# =============================================================================
# Run: streamlit run streamlit_app.py
# Backend: BACKEND_URL (default http://127.0.0.1:8000)
# =============================================================================

import os
import streamlit as st
import requests

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# No trailing slash so paths like /generate work
BASE_URL = (os.environ.get("BACKEND_URL") or "http://127.0.0.1:8000").rstrip("/")


def fetch_post_json(path: str, json_payload: dict) -> dict | None:
    path = path if path.startswith("/") else "/" + path
    url = f"{BASE_URL}{path}"
    try:
        r = requests.post(url, json=json_payload, timeout=90)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            st.error(f"Not Found (404). Backend may be wrong or outdated. Using: {BASE_URL}. Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000` then restart the UI.")
        else:
            st.error(f"Request failed: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


def fetch_json(path: str) -> dict | list | None:
    path = path if path.startswith("/") else "/" + path
    url = f"{BASE_URL}{path}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            st.error(f"Not Found (404). Backend may be wrong or outdated. Using: {BASE_URL}")
        else:
            st.error(f"Request failed: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


st.set_page_config(page_title="OmniTutor AI", layout="centered")
st.title("OmniTutor AI")
with st.sidebar:
    st.caption(f"Backend: `{BASE_URL}`")
    st.caption("Start both: `python run.py`")

tab_ask, tab_dashboard = st.tabs(["Ask", "Dashboard"])

# -----------------------------------------------------------------------------
# Ask — question panel and output only; model chosen automatically
# -----------------------------------------------------------------------------
with tab_ask:
    st.subheader("Ask a question")
    prompt = st.text_area(
        "Question",
        placeholder="e.g. In which year did the USSR fall?",
        height=120,
        label_visibility="collapsed",
    )
    if st.button("Ask", type="primary"):
        if not (prompt and prompt.strip()):
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                body = {
                    "provider": "auto",
                    "model": "",
                    "prompt": prompt.strip(),
                    "temperature": 0.7,
                }
                out = fetch_post_json("/generate", body)
            if out:
                st.divider()
                st.subheader("Answer")
                st.write(out.get("response", ""))
                st.caption(f"Provider: {out.get('provider_used', '—')} · Latency: {out.get('latency_ms', '—')} ms")
            else:
                st.info("No response. Check backend is running and API keys are set.")

# -----------------------------------------------------------------------------
# Dashboard — daily usage and question categories only
# -----------------------------------------------------------------------------
with tab_dashboard:
    st.subheader("Dashboard")
    data = fetch_json("/dashboard/stats")
    if data is None:
        st.info("Could not load dashboard. Is the backend running?")
    else:
        daily = data.get("daily_usage") or []
        categories = data.get("categories") or []

        st.subheader("Daily usage")
        if not daily:
            st.caption("No usage data yet. Ask some questions in the Ask tab.")
        elif HAS_PLOTLY:
            dates = [d["date"] for d in daily]
            counts = [d["count"] for d in daily]
            fig = go.Figure(data=[go.Bar(x=dates, y=counts, name="Questions")])
            fig.update_layout(
                title="Questions per day (last 30 days)",
                xaxis_title="Date",
                yaxis_title="Count",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            for d in daily:
                st.write(f"**{d['date']}**: {d['count']} questions")
            st.caption("Install plotly for charts: pip install plotly")

        st.subheader("Question categories")
        if not categories:
            st.caption("No category data yet.")
        elif HAS_PLOTLY:
            names = [c["name"] for c in categories]
            counts = [c["count"] for c in categories]
            fig2 = go.Figure(data=[go.Pie(labels=names, values=counts, hole=0.4)])
            fig2.update_layout(
                title="Types of questions asked",
                height=350,
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            for c in categories:
                st.write(f"- **{c['name']}**: {c['count']}")
            st.caption("Install plotly for charts: pip install plotly")
