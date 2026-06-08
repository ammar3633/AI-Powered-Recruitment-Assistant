"""
Interview Scheduler Interface
Schedule and manage interviews with candidates
"""

import streamlit as st
from datetime import datetime, timedelta
from mcp_servers import get_ats_mcp, get_calendar_mcp

st.set_page_config(page_title="Interview Scheduler", layout="wide")

st.title("📅 Interview Scheduler")
st.markdown("Schedule and manage interviews efficiently")

ats = get_ats_mcp()
calendar = get_calendar_mcp()

# Tabs
tab1, tab2, tab3 = st.tabs(["Schedule Interview", "Scheduled Interviews", "Availability Management"])

# Tab 1: Schedule Interview
with tab1:
    st.header("Schedule New Interview")

    with st.form("schedule_interview_form"):
        col1, col2 = st.columns(2)

        with col1:
            # Get candidates who are shortlisted
            candidates = ats.list_candidates()
            shortlisted = [c for c in candidates if c.get("status") == "shortlisted"]

            if shortlisted:
                candidate_options = {c.get("name", ""): c["id"] for c in shortlisted}
                selected_candidate = st.selectbox("Select Candidate", list(candidate_options.keys()))
                candidate_id = candidate_options[selected_candidate]
            else:
                st.warning("No shortlisted candidates available")
                candidate_id = None

        with col2:
            jobs = ats.list_job_postings(status="open")
            job_options = {j.get("title", ""): j["id"] for j in jobs}
            selected_job = st.selectbox("Select Job Position", list(job_options.keys()))
            job_id = job_options[selected_job]

        col1, col2 = st.columns(2)

        with col1:
            interview_date = st.date_input(
                "Interview Date",
                value=datetime.now() + timedelta(days=3),
                min_value=datetime.now()
            )

        with col2:
            interview_time = st.time_input("Interview Time", value=datetime.now().time())

        col1, col2 = st.columns(2)

        with col1:
            interview_type = st.selectbox("Interview Type", ["Phone Call", "Video Call", "In-Person"])

        with col2:
            interviewer = st.selectbox(
                "Interviewer",
                ["Hiring Manager", "Team Lead", "HR Manager", "Technical Lead"]
            )

        meeting_link = ""
        if interview_type == "Video Call":
            meeting_link = st.text_input(
                "Meeting Link (optional)",
                value="https://meet.example.com/interview"
            )

        notes = st.text_area("Interview Notes (optional)", height=100)

        submitted = st.form_submit_button("Schedule Interview")

        if submitted:
            if candidate_id and job_id:
                st.info("📧 Scheduling interview...")

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

                st.success(f"✅ Interview scheduled successfully!")
                st.write(f"**Event ID:** {event_id}")
                st.write(f"**Candidate:** {selected_candidate}")
                st.write(f"**Position:** {selected_job}")
                st.write(f"**Date & Time:** {interview_datetime.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Type:** {interview_type}")

                if meeting_link:
                    st.write(f"**Meeting Link:** {meeting_link}")

# Tab 2: Scheduled Interviews
with tab2:
    st.header("Scheduled Interviews")

    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "Scheduled", "Completed", "Rescheduled", "Cancelled"]
    )

    all_interviews = calendar.list_scheduled_interviews()

    if all_interviews:
        # Sort by scheduled time
        sorted_interviews = sorted(
            all_interviews,
            key=lambda x: x.get("scheduled_time", ""),
            reverse=True
        )

        for interview in sorted_interviews:
            status = interview.get("status", "scheduled")

            # Status color coding
            if status == "scheduled":
                status_color = "🟢"
            elif status == "completed":
                status_color = "🔵"
            elif status == "rescheduled":
                status_color = "🟡"
            else:  # cancelled
                status_color = "🔴"

            with st.expander(f"{status_color} {interview.get('candidate_name', 'Unknown')} - {interview.get('job_title', 'Unknown')}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Candidate:** {interview.get('candidate_name')}")
                    st.write(f"**Job:** {interview.get('job_title')}")
                    st.write(f"**Type:** {interview.get('interview_type')}")

                with col2:
                    st.write(f"**Interviewer:** {interview.get('interviewer')}")
                    st.write(f"**Time:** {interview.get('scheduled_time')}")
                    st.write(f"**Status:** {status}")

                with col3:
                    if interview.get("meeting_link"):
                        st.write(f"**Meeting Link:** {interview['meeting_link']}")
                    if interview.get("feedback"):
                        st.write(f"**Feedback:** {interview['feedback'][:100]}...")

                # Action buttons
                col1, col2, col3 = st.columns(3)

                with col1:
                    if status == "scheduled":
                        if st.button("Reschedule", key=f"reschedule_{interview['id']}"):
                            st.write("Open reschedule dialog...")

                with col2:
                    if status in ["scheduled", "rescheduled"]:
                        if st.button("Mark Completed", key=f"complete_{interview['id']}"):
                            feedback = st.text_area(
                                "Interview Feedback",
                                key=f"feedback_{interview['id']}"
                            )
                            rating = st.slider(
                                "Rating",
                                0.0,
                                5.0,
                                2.5,
                                key=f"rating_{interview['id']}"
                            )
                            if st.button("Submit Feedback"):
                                st.success("Interview feedback submitted!")

                with col3:
                    if st.button("Cancel", key=f"cancel_{interview['id']}"):
                        st.write("Interview cancelled.")

    else:
        st.info("No scheduled interviews")

# Tab 3: Availability Management
with tab3:
    st.header("Interviewer Availability Management")

    st.subheader("Add Availability")

    with st.form("add_availability_form"):
        interviewer = st.selectbox("Interviewer", [
            "Hiring Manager",
            "Team Lead",
            "HR Manager",
            "Technical Lead",
        ])

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Available From (Date)")
            start_time = st.time_input("From (Time)", value=datetime.strptime("09:00", "%H:%M").time())

        with col2:
            end_date = st.date_input("Available To (Date)")
            end_time = st.time_input("To (Time)", value=datetime.strptime("17:00", "%H:%M").time())

        availability_type = st.selectbox("Availability Type", [
            "Daily",
            "Weekly",
            "One-time"
        ])

        submitted = st.form_submit_button("Add Availability")

        if submitted:
            st.success(f"✅ Availability added for {interviewer}")
            st.write(f"Available: {start_date} {start_time} to {end_date} {end_time}")

    st.markdown("---")

    st.subheader("Current Availability")

    interviewers = [
        "Hiring Manager",
        "Team Lead",
        "HR Manager",
        "Technical Lead",
    ]

    for interviewer in interviewers:
        with st.expander(f"📅 {interviewer}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write("**Monday - Friday**")
                st.write("9:00 AM - 5:00 PM")

            with col2:
                st.write("**Booked Slots**")
                st.write("10:00-11:00")
                st.write("2:00-3:00")

            with col3:
                st.write("**Available Slots**")
                st.write("9:00-10:00")
                st.write("11:00-2:00")

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
