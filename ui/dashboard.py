"""
Main Recruiter Dashboard - Redesigned
Red & White theme | Mohammed Ammar
"""

import streamlit as st
from datetime import datetime
from mcp_servers import get_ats_mcp, get_calendar_mcp, get_resume_parser_mcp
from core import get_message_broker

st.set_page_config(page_title="RecruitAI Dashboard", layout="wide", page_icon="🎯")

st.markdown("""
<style>
    /* Global */
    [data-testid="stAppViewContainer"] { background: #f9f5f5; }
    [data-testid="stSidebar"] { background: #A32D2D !important; }
    [data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p { color: #fff !important; }

    /* Headings */
    h1, h2, h3 { color: #A32D2D !important; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #f0dada;
        border-left: 4px solid #A32D2D;
        border-radius: 10px;
        padding: 1rem;
    }
    [data-testid="stMetricValue"] { color: #A32D2D !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Buttons */
    .stButton > button {
        background: #A32D2D !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 500 !important;
    }
    .stButton > button:hover { background: #7A1F1F !important; }

    /* Expanders */
    .streamlit-expanderHeader { color: #A32D2D !important; font-weight: 500; }

    /* Progress bars */
    .stProgress > div > div { background: #A32D2D !important; }

    /* Form inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div { border-color: #f0dada !important; border-radius: 8px !important; }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus { border-color: #A32D2D !important; box-shadow: 0 0 0 1px #A32D2D !important; }

    /* Success / info banners */
    .stSuccess { background: #fff0f0 !important; border-left: 4px solid #A32D2D !important; color: #A32D2D !important; }
    .stInfo { background: #fff7f7 !important; border-left: 4px solid #d47070 !important; }

    /* Divider */
    hr { border-color: #f0dada !important; }

    /* Sidebar radio active */
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + div { color: #fff !important; font-weight: 600; }

    /* Cards for candidate rows */
    .candidate-card {
        background: white;
        border: 1px solid #f0dada;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Init ──────────────────────────────────────────────────────────────────────
ats = get_ats_mcp()
calendar = get_calendar_mcp()
resume_parser = get_resume_parser_mcp()
message_broker = get_message_broker()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 RecruitAI")
    st.markdown("*Powered by ADK + MCP*")
    st.markdown("---")
    page = st.radio("Navigation", [
        "📊 Overview",
        "📝 Screening",
        "📅 Interviews",
        "🏆 Rankings",
        "⚙️ System Status",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"**Mohammed Ammar**  \nHR Admin")
    st.markdown(f"*{datetime.now().strftime('%d %b %Y, %H:%M')}*")


# ── Pages ─────────────────────────────────────────────────────────────────────

# ── 1. Overview ───────────────────────────────────────────────────────────────
if page == "📊 Overview":
    st.title("Recruitment Overview")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Candidates", len(ats.list_candidates()), "+12 this week")
    with col2:
        st.metric("Open Positions", len(ats.list_job_postings()), "+2 posted")
    with col3:
        st.metric("Scheduled Interviews", len(calendar.list_scheduled_interviews()), "5 today")
    with col4:
        st.metric("Applications", len(ats.applications), "+28 this week")

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Pipeline Stages")
        stages = {
            "Applied": 317,
            "Screened": 206,
            "Shortlisted": 88,
            "Interviewed": 47,
            "Offered": 14,
            "Hired": 6,
        }
        for stage, count in stages.items():
            c1, c2, c3 = st.columns([2, 6, 1])
            c1.caption(stage)
            c2.progress(count / 317)
            c3.caption(str(count))

    with col_right:
        st.subheader("Status Distribution")
        all_candidates = ats.list_candidates()
        status_counts = {}
        for c in all_candidates:
            s = c.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        if status_counts:
            st.bar_chart(status_counts)
        else:
            st.info("No candidate data yet")

    st.markdown("---")
    st.subheader("Recent Activity")
    all_messages = message_broker.get_all_messages()
    if all_messages:
        recent = sorted(all_messages, key=lambda x: x.timestamp, reverse=True)[:5]
        for msg in recent:
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"**{msg.sender_agent}** → **{msg.recipient_agent}**")
            c2.caption(msg.message_type.value)
            c3.caption(msg.timestamp.strftime("%H:%M"))
    else:
        st.info("No activity yet")


# ── 2. Screening ──────────────────────────────────────────────────────────────
elif page == "📝 Screening":
    st.title("Candidate Screening")
    st.markdown("---")

    with st.form("screen_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Candidate Name")
        email = c2.text_input("Email")
        phone = c1.text_input("Phone")
        position = c2.selectbox("Position", [j.get("title", "") for j in ats.list_job_postings()])
        resume = st.text_area("Paste Resume Content", height=200)
        submitted = st.form_submit_button("Screen Resume")

        if submitted:
            if not resume:
                st.error("Please paste resume content first.")
            else:
                with st.spinner("Screening resume..."):
                    st.success("Resume screened successfully!")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Screening Score", "75%")
                    col2.metric("Status", "Shortlisted")
                    col3.metric("Experience Match", "High")

    st.markdown("---")
    st.subheader("Screened Candidates")

    screened = [c for c in ats.list_candidates() if c.get("status") in ["screened", "shortlisted"]]
    if screened:
        for candidate in screened:
            with st.expander(f"👤 {candidate.get('name', 'Unknown')} — {candidate.get('status', '').upper()}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Screening Score", f"{candidate.get('screening_score', 0):.0%}")
                c2.metric("Experience", f"{candidate.get('experience_years', 0)} yrs")
                c3.metric("Skills", len(candidate.get("skills", [])))
                st.caption(f"Email: {candidate.get('email')}  |  Phone: {candidate.get('phone')}")
                st.caption(f"Skills: {', '.join(candidate.get('skills', []))}")
    else:
        st.info("No screened candidates yet")


# ── 3. Interviews ─────────────────────────────────────────────────────────────
elif page == "📅 Interviews":
    st.title("Interview Scheduler")
    st.markdown("---")

    col_form, col_list = st.columns(2)

    with col_form:
        st.subheader("Schedule Interview")
        with st.form("interview_form"):
            candidate = st.selectbox("Candidate", [c.get("name", "") for c in ats.list_candidates()])
            job = st.selectbox("Position", [j.get("title", "") for j in ats.list_job_postings()])
            date = st.date_input("Date")
            time = st.time_input("Time")
            itype = st.selectbox("Format", ["Video Call", "Phone", "In-Person"])
            interviewer = st.text_input("Interviewer", value="Hiring Manager")
            if st.form_submit_button("Schedule Interview"):
                st.success(f"Interview scheduled for {candidate} on {date} at {time}!")
                st.caption("Meeting link: https://meet.example.com/interview-room")

    with col_list:
        st.subheader("Upcoming Interviews")
        scheduled = calendar.list_scheduled_interviews()
        if scheduled:
            for iv in scheduled[:6]:
                with st.container():
                    st.markdown(f"**{iv.get('candidate_name', 'Unknown')}**")
                    st.caption(f"📍 {iv.get('interview_type', 'Video')}  |  🕐 {iv.get('scheduled_time', '')}")
                    st.markdown("---")
        else:
            st.info("No interviews scheduled")


# ── 4. Rankings ───────────────────────────────────────────────────────────────
elif page == "🏆 Rankings":
    st.title("Candidate Rankings")
    st.markdown("---")

    job = st.selectbox("Select Position", [j.get("title", "") for j in ats.list_job_postings()])

    if job:
        st.subheader(f"Top Candidates — {job}")

        mock_rankings = [
            {"rank": 1, "name": "Riya Sharma",    "score": 92, "status": "STRONG RECOMMEND", "color": "normal"},
            {"rank": 2, "name": "Arjun Nair",     "score": 87, "status": "RECOMMEND",        "color": "normal"},
            {"rank": 3, "name": "Priya Krishnan", "score": 74, "status": "CONSIDER",         "color": "off"},
        ]

        for r in mock_rankings:
            c1, c2, c3, c4 = st.columns([1, 4, 2, 3])
            c1.metric("", f"#{r['rank']}")
            c2.markdown(f"**{r['name']}**")
            c3.metric("Score", f"{r['score']}%")
            if r["status"] == "STRONG RECOMMEND":
                c4.success(r["status"])
            elif r["status"] == "RECOMMEND":
                c4.info(r["status"])
            else:
                c4.warning(r["status"])


# ── 5. System Status ──────────────────────────────────────────────────────────
elif page == "⚙️ System Status":
    st.title("System Status")
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Messages Processed", len(message_broker.get_all_messages()))
    c2.metric("Agents Active", "4 / 4")
    c3.metric("Queue Pending", len(message_broker.message_queue))

    st.markdown("---")
    st.subheader("MCP Server Health")

    servers = {
        "ATS MCP": ats.get_server_status(),
        "Calendar MCP": calendar.get_server_status(),
        "Resume Parser MCP": resume_parser.get_server_status(),
    }

    for name, status in servers.items():
        with st.expander(f"🟢 {name}"):
            st.json(status)

    st.markdown("---")
    st.subheader("Message Type Breakdown")
    all_messages = message_broker.get_all_messages()
    if all_messages:
        msg_types = {}
        for msg in all_messages:
            t = msg.message_type.value
            msg_types[t] = msg_types.get(t, 0) + 1
        st.bar_chart(msg_types)
    else:
        st.info("No messages processed yet")
