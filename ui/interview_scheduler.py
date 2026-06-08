"""
Interview Scheduler Interface - Redesigned
Red & White theme | Mohammed Ammar
"""

import streamlit as st
from datetime import datetime, timedelta
from mcp_servers import get_ats_mcp, get_calendar_mcp

st.set_page_config(page_title="Interview Scheduler", layout="wide", page_icon="📅")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f9f5f5; }
    [data-testid="stSidebar"] { background: #A32D2D !important; }
    [data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }

    h1, h2, h3 { color: #A32D2D !important; }

    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #f0dada;
        border-left: 4px solid #A32D2D;
        border-radius: 10px;
        padding: 1rem;
    }
    [data-testid="stMetricValue"] { color: #A32D2D !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.05em; }

    .stButton > button {
        background: #A32D2D !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 500 !important;
    }
    .stButton > button:hover { background: #7A1F1F !important; }

    .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #f0dada; }
    .stTabs [data-baseweb="tab"] { color: #888 !important; }
    .stTabs [aria-selected="true"] { color: #A32D2D !important; border-bottom: 2px solid #A32D2D !important; }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        border-color: #f0dada !important;
        border-radius: 8px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #A32D2D !important;
        box-shadow: 0 0 0 1px #A32D2D !important;
    }

    .stSuccess { background: #fff0f0 !important; border-left: 4px solid #A32D2D !important; color: #A32D2D !important; }
    .stInfo    { background: #fff7f7 !important; border-left: 4px solid #d47070 !important; }
    .stWarning { background: #fffaf0 !important; border-left: 4px solid #e0a030 !important; }

    hr { border-color: #f0dada !important; }

    .streamlit-expanderHeader { color: #A32D2D !important; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
ats = get_ats_mcp()
calendar = get_calendar_mcp()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📅 Interview Scheduler")
st.caption("Schedule and manage interviews across your recruitment pipeline")
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["  Schedule Interview  ", "  Scheduled Interviews  ", "  Availability  "])


# ── Tab 1: Schedule Interview ─────────────────────────────────────────────────
with tab1:
    st.subheader("Schedule New Interview")

    with st.form("schedule_interview_form"):
        c1, c2 = st.columns(2)

        with c1:
            candidates = ats.list_candidates()
            shortlisted = [c for c in candidates if c.get("status") == "shortlisted"]
            if shortlisted:
                candidate_options = {c.get("name", "Unknown"): c["id"] for c in shortlisted}
                selected_candidate = st.selectbox("Candidate", list(candidate_options.keys()))
                candidate_id = candidate_options[selected_candidate]
            else:
                st.warning("No shortlisted candidates available")
                selected_candidate = None
                candidate_id = None

        with c2:
            jobs = ats.list_job_postings(status="open")
            if jobs:
                job_options = {j.get("title", "Unknown"): j["id"] for j in jobs}
            else:
                job_options = {"No positions available": None}
            selected_job = st.selectbox("Position", list(job_options.keys()))
            job_id = job_options[selected_job]

        c1, c2 = st.columns(2)
        with c1:
            interview_date = st.date_input(
                "Interview Date",
                value=datetime.now() + timedelta(days=3),
                min_value=datetime.now().date()
            )
        with c2:
            interview_time = st.time_input("Interview Time", value=datetime.strptime("10:00", "%H:%M").time())

        c1, c2 = st.columns(2)
        with c1:
            interview_type = st.selectbox("Format", ["Video Call", "Phone Call", "In-Person"])
        with c2:
            interviewer = st.selectbox("Interviewer", ["Hiring Manager", "Team Lead", "HR Manager", "Technical Lead"])

        meeting_link = ""
        if interview_type == "Video Call":
            meeting_link = st.text_input("Meeting Link (optional)", value="https://meet.example.com/interview")

        notes = st.text_area("Notes (optional)", height=80)

        submitted = st.form_submit_button("Schedule Interview")

        if submitted:
            if candidate_id and job_id:
                interview_datetime = datetime.combine(interview_date, interview_time)
                interview_data = {
                    "candidate_id": candidate_id,
                    "candidate_name": selected_candidate,
                    "job_id": job_id,
                    "job_title": selected_job,
                    "scheduled_time": interview_datetime.isoformat(),
                    "interviewer": interviewer,
                    "interview_type": interview_type,
                    "meeting_link": meeting_link,
                    "notes": notes,
                }
                event_id = calendar.schedule_interview(interview_data)

                st.success("Interview scheduled successfully!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Candidate", selected_candidate)
                c2.metric("Date", interview_datetime.strftime("%d %b %Y"))
                c3.metric("Time", interview_datetime.strftime("%H:%M"))

                if meeting_link:
                    st.info(f"Meeting Link: {meeting_link}")
            else:
                st.error("Please select a valid candidate and position.")


# ── Tab 2: Scheduled Interviews ───────────────────────────────────────────────
with tab2:
    st.subheader("All Scheduled Interviews")

    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "Scheduled", "Completed", "Rescheduled", "Cancelled"],
        label_visibility="collapsed"
    )

    all_interviews = calendar.list_scheduled_interviews()

    if all_interviews:
        sorted_interviews = sorted(
            all_interviews,
            key=lambda x: x.get("scheduled_time", ""),
            reverse=True
        )

        if filter_status != "All":
            sorted_interviews = [
                i for i in sorted_interviews
                if i.get("status", "scheduled").lower() == filter_status.lower()
            ]

        if not sorted_interviews:
            st.info(f"No interviews with status: {filter_status}")
        else:
            for iv in sorted_interviews:
                status = iv.get("status", "scheduled").lower()
                icon = {"scheduled": "🟢", "completed": "🔵", "rescheduled": "🟡", "cancelled": "🔴"}.get(status, "⚪")

                with st.expander(f"{icon} {iv.get('candidate_name', 'Unknown')} — {iv.get('job_title', 'Unknown')}"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Candidate:** {iv.get('candidate_name', '—')}")
                    c1.markdown(f"**Position:** {iv.get('job_title', '—')}")
                    c1.markdown(f"**Format:** {iv.get('interview_type', '—')}")

                    c2.markdown(f"**Interviewer:** {iv.get('interviewer', '—')}")
                    c2.markdown(f"**Time:** {iv.get('scheduled_time', '—')}")
                    c2.markdown(f"**Status:** {status.capitalize()}")

                    if iv.get("meeting_link"):
                        c3.markdown(f"**Meeting Link:** {iv['meeting_link']}")
                    if iv.get("feedback"):
                        c3.markdown(f"**Feedback:** {str(iv['feedback'])[:100]}...")

                    st.markdown("---")
                    b1, b2, b3 = st.columns(3)

                    with b1:
                        if status == "scheduled":
                            if st.button("Reschedule", key=f"reschedule_{iv.get('id', iv.get('candidate_name', ''))}"):
                                st.info("Reschedule dialog would open here.")

                    with b2:
                        if status in ["scheduled", "rescheduled"]:
                            if st.button("Mark Completed", key=f"complete_{iv.get('id', iv.get('candidate_name', ''))}"):
                                st.success("Marked as completed.")

                    with b3:
                        if st.button("Cancel", key=f"cancel_{iv.get('id', iv.get('candidate_name', ''))}"):
                            st.warning("Interview cancelled.")
    else:
        st.info("No scheduled interviews yet.")


# ── Tab 3: Availability ───────────────────────────────────────────────────────
with tab3:
    st.subheader("Manage Interviewer Availability")

    col_form, col_current = st.columns(2)

    with col_form:
        st.markdown("**Add Availability**")
        with st.form("add_availability_form"):
            interviewer = st.selectbox("Interviewer", ["Hiring Manager", "Team Lead", "HR Manager", "Technical Lead"])

            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("From Date", value=datetime.now().date())
                start_time = st.time_input("From Time", value=datetime.strptime("09:00", "%H:%M").time())
            with c2:
                end_date = st.date_input("To Date", value=datetime.now().date())
                end_time = st.time_input("To Time", value=datetime.strptime("17:00", "%H:%M").time())

            avail_type = st.selectbox("Type", ["Daily", "Weekly", "One-time"])

            if st.form_submit_button("Add Availability"):
                st.success(f"Availability added for {interviewer}")
                st.caption(f"{start_date} {start_time.strftime('%H:%M')} → {end_date} {end_time.strftime('%H:%M')} ({avail_type})")

    with col_current:
        st.markdown("**Current Availability**")
        interviewers = ["Hiring Manager", "Team Lead", "HR Manager", "Technical Lead"]
        for person in interviewers:
            with st.expander(f"📅 {person}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown("**Schedule**\nMon–Fri\n9:00–17:00")
                c2.markdown("**Booked**\n10:00–11:00\n14:00–15:00")
                c3.markdown("**Free**\n9:00–10:00\n11:00–14:00")

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
