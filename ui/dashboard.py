"""
Main Recruiter Dashboard
Overview of recruitment pipeline and system status
"""

import streamlit as st
from datetime import datetime
from mcp_servers import get_ats_mcp, get_calendar_mcp, get_resume_parser_mcp
from core import get_message_broker

st.set_page_config(page_title="Recruiter Dashboard", layout="wide")

st.title("🎯 AI-Powered Recruitment Dashboard")
st.markdown("---")

# Initialize MCP servers
ats = get_ats_mcp()
calendar = get_calendar_mcp()
resume_parser = get_resume_parser_mcp()
message_broker = get_message_broker()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "Dashboard Overview",
    "Candidate Screening",
    "Interview Scheduler",
    "Candidate Ranking",
    "System Status",
])

# Dashboard Overview Page
if page == "Dashboard Overview":
    st.header("📊 Recruitment Pipeline Overview")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        candidates = len(ats.list_candidates())
        st.metric("Total Candidates", candidates)

    with col2:
        jobs = len(ats.list_job_postings())
        st.metric("Open Positions", jobs)

    with col3:
        interviews = len(calendar.list_scheduled_interviews())
        st.metric("Scheduled Interviews", interviews)

    with col4:
        applications = len(ats.applications)
        st.metric("Applications", applications)

    st.markdown("---")

    # Candidate Status Distribution
    st.subheader("📈 Candidate Status Distribution")

    all_candidates = ats.list_candidates()
    status_counts = {}

    for candidate in all_candidates:
        status = candidate.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    if status_counts:
        st.bar_chart(status_counts)
    else:
        st.info("No candidate data available")

    st.markdown("---")

    # Recent Activities
    st.subheader("⏱️ Recent Activities")

    all_messages = message_broker.get_all_messages()
    if all_messages:
        recent_messages = sorted(all_messages, key=lambda x: x.timestamp, reverse=True)[:5]

        for msg in recent_messages:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.text(f"**{msg.sender_agent}** → **{msg.recipient_agent}**")
                with col2:
                    st.text(f"{msg.message_type.value}")
                with col3:
                    st.text(msg.timestamp.strftime("%H:%M:%S"))
    else:
        st.info("No activities yet")

# Candidate Screening Page
elif page == "Candidate Screening":
    st.header("📝 Candidate Screening Portal")

    with st.form("screening_form"):
        col1, col2 = st.columns(2)

        with col1:
            candidate_name = st.text_input("Candidate Name")
            candidate_email = st.text_input("Email")

        with col2:
            candidate_phone = st.text_input("Phone")
            job_position = st.selectbox("Job Position", [j.get("title", "") for j in ats.list_job_postings()])

        resume_text = st.text_area("Paste Resume Content", height=300)

        submitted = st.form_submit_button("Screen Resume")

        if submitted:
            if not resume_text:
                st.error("Please paste resume content")
            else:
                st.info("Resume screening initiated...")
                # In production, this would call the Resume Screening Agent
                st.success("Resume screened successfully!")
                st.write("Screening Score: 0.75 (75%)")
                st.write("Status: SHORTLISTED")

    st.markdown("---")

    # List of screened candidates
    st.subheader("🔍 Screened Candidates")

    screened = [c for c in ats.list_candidates() if c.get("status") in ["screened", "shortlisted"]]

    if screened:
        for candidate in screened:
            with st.expander(f"👤 {candidate.get('name', 'Unknown')}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Screening Score", f"{candidate.get('screening_score', 0):.1%}")
                with col2:
                    st.metric("Experience", f"{candidate.get('experience_years', 0)} years")
                with col3:
                    st.metric("Skills", len(candidate.get("skills", [])))

                st.write(f"**Email:** {candidate.get('email')}")
                st.write(f"**Phone:** {candidate.get('phone')}")
                st.write(f"**Skills:** {', '.join(candidate.get('skills', []))}")
    else:
        st.info("No screened candidates yet")

# Interview Scheduler Page
elif page == "Interview Scheduler":
    st.header("📅 Interview Scheduler")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Schedule New Interview")
        with st.form("interview_form"):
            candidate = st.selectbox("Select Candidate", [c.get("name", "") for c in ats.list_candidates()])
            job = st.selectbox("Select Job", [j.get("title", "") for j in ats.list_job_postings()])
            interview_date = st.date_input("Interview Date")
            interview_time = st.time_input("Interview Time")
            interview_type = st.selectbox("Interview Type", ["Phone", "Video", "In-Person"])
            interviewer = st.text_input("Interviewer Name", value="Hiring Manager")

            if st.form_submit_button("Schedule Interview"):
                st.success("Interview scheduled successfully!")
                st.write(f"Meeting Link: https://meet.example.com/interview")

    with col2:
        st.subheader("Scheduled Interviews")
        scheduled = calendar.list_scheduled_interviews()

        if scheduled:
            for interview in scheduled[:5]:
                with st.container():
                    st.write(f"**{interview.get('candidate_name', 'Unknown')}**")
                    st.write(f"📍 {interview.get('interview_type', 'Video')}")
                    st.write(f"🕐 {interview.get('scheduled_time')}")
                    st.write("---")
        else:
            st.info("No scheduled interviews")

# Candidate Ranking Page
elif page == "Candidate Ranking":
    st.header("🏆 Candidate Ranking Dashboard")

    job_select = st.selectbox("Select Job", [j.get("title", "") for j in ats.list_job_postings()])

    if job_select:
        st.subheader(f"Top Candidates for {job_select}")

        # Mock ranking data
        mock_rankings = [
            {"rank": 1, "name": "John Doe", "score": 92, "status": "STRONG_RECOMMEND"},
            {"rank": 2, "name": "Jane Smith", "score": 87, "status": "RECOMMEND"},
            {"rank": 3, "name": "Bob Johnson", "score": 78, "status": "CONSIDER"},
        ]

        for rank in mock_rankings:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Rank", rank["rank"])
            with col2:
                st.write(rank["name"])
            with col3:
                st.metric("Score", f"{rank['score']}%")
            with col4:
                if rank["status"] == "STRONG_RECOMMEND":
                    st.success(rank["status"])
                elif rank["status"] == "RECOMMEND":
                    st.info(rank["status"])
                else:
                    st.warning(rank["status"])

# System Status Page
elif page == "System Status":
    st.header("⚙️ System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("ATS MCP")
        ats_status = ats.get_server_status()
        st.json(ats_status)

    with col2:
        st.subheader("Calendar MCP")
        calendar_status = calendar.get_server_status()
        st.json(calendar_status)

    with col3:
        st.subheader("Resume Parser MCP")
        parser_status = resume_parser.get_server_status()
        st.json(parser_status)

    st.markdown("---")

    st.subheader("📋 Message Broker Statistics")
    all_messages = message_broker.get_all_messages()
    st.metric("Total Messages Processed", len(all_messages))
    st.metric("Pending Messages", len(message_broker.message_queue))

    if all_messages:
        message_types = {}
        for msg in all_messages:
            msg_type = msg.message_type.value
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

        st.bar_chart(message_types)

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
