import streamlit as st
import requests
import os

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:5000")

st.set_page_config(
    page_title="Task Manager",
    page_icon="✅",
    layout="centered",
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API. Is it running?"
    except requests.exceptions.HTTPError as e:
        return None, str(e)


def api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API. Is it running?"
    except requests.exceptions.HTTPError as e:
        return None, e.response.json().get("error", str(e))


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API. Is it running?"
    except requests.exceptions.HTTPError as e:
        return None, e.response.json().get("error", str(e))


# ── Sidebar – API health ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    st.caption(f"API: `{API_BASE}`")

    health_data, err = api_get("/health")
    if health_data:
        st.success(f"API is **healthy** ✅")
        st.caption(f"Checked at: {health_data.get('timestamp', '')}")
    else:
        st.error(f"API unreachable ❌\n\n{err}")

    if st.button("🔄 Refresh"):
        st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("✅ Task Manager")
st.write("A simple task tracker powered by Flask + Streamlit.")

st.divider()

# ── Create task ───────────────────────────────────────────────────────────────
st.subheader("➕ Add a New Task")

with st.form("create_task_form", clear_on_submit=True):
    title = st.text_input("Title *", placeholder="e.g. Buy groceries")
    description = st.text_area("Description", placeholder="Optional details…", height=80)
    submitted = st.form_submit_button("Create Task", use_container_width=True)

if submitted:
    if not title.strip():
        st.warning("Title is required.")
    else:
        result, err = api_post("/tasks", {"title": title.strip(), "description": description.strip()})
        if result:
            st.success(f"Task **#{result['id']}** created: *{result['title']}*")
        else:
            st.error(f"Failed to create task: {err}")

st.divider()

# ── Task list ─────────────────────────────────────────────────────────────────
st.subheader("📋 All Tasks")

data, err = api_get("/tasks")

if err:
    st.error(err)
elif data and data["count"] == 0:
    st.info("No tasks yet. Add one above!")
else:
    tasks = data["tasks"]
    st.caption(f"{data['count']} task(s) found")

    for task in tasks:
        with st.container(border=True):
            col_info, col_btn = st.columns([5, 1])

            with col_info:
                status_icon = "✅" if task["done"] else "🔲"
                st.markdown(f"**{status_icon} #{task['id']} — {task['title']}**")
                if task["description"]:
                    st.caption(task["description"])
                st.caption(f"Created: {task['created_at']}")

            with col_btn:
                if st.button("🗑️", key=f"del_{task['id']}", help="Delete this task"):
                    result, err = api_delete(f"/tasks/{task['id']}")
                    if result:
                        st.success(f"Task #{task['id']} deleted.")
                        st.rerun()
                    else:
                        st.error(err)
