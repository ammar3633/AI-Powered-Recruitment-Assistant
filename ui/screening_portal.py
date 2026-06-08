"""
Candidate Screening Portal
Dedicated interface for screening candidates
"""

import streamlit as st
from mcp_servers import get_ats_mcp, get_resume_parser_mcp

st.set_page_config(page_title="Candidate Screening Portal", layout="wide")

st.title("📋 Candidate Screening Portal")
st.markdown("Evaluate and shortlist candidates for open positions")

ats = get_ats_mcp()
resume_parser = get_resume_parser_mcp()

# Tab interface
tab1, tab2, tab3 = st.tabs(["New Resume", "Candidate Pool", "Screening Reports"])

# Tab 1: New Resume
with tab1:
    st.header("Submit New Resume")

    col1, col2 = st.columns(2)

    with col1:
        candidate_name = st.text_input("Candidate Name", key="name_input")
        candidate_email = st.text_input("Email Address", key="email_input")
        candidate_phone = st.text_input("Phone Number", key="phone_input")

    with col2:
        job_position = st.selectbox("Applying For Position", 
                                   [j.get("title", "") for j in ats.list_job_postings()] + ["Other"])
        years_experience = st.number_input("Years of Experience", min_value=0, max_value=50)

    resume_file = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])

    if st.button("Screen Resume", key="screen_btn"):
        if not candidate_name or not resume_file:
            st.error("Please fill in all required fields")
        else:
            st.info("Processing resume...")

            resume_content = resume_file.read().decode("utf-8", errors="ignore")
            resume_id = resume_parser.parse_resume(resume_content, resume_file.name)

            profile = resume_parser.extract_candidate_profile(resume_id)
            validation = resume_parser.validate_resume(resume_id)

            # Display results
            col1, col2, col3 = st.columns(3)

            with col1:
                completeness = validation.get("completeness_score", 0)
                st.metric("Resume Completeness", f"{completeness:.0f}%")

            with col2:
                skills_count = len(profile.get("skills", []))
                st.metric("Skills Detected", skills_count)

            with col3:
                exp_years = profile.get("experience_years", 0)
                st.metric("Experience", f"{exp_years} years")

            st.markdown("---")

            # Detailed profile
            st.subheader("Extracted Profile")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Name:** {profile.get('name', 'N/A')}")
                st.write(f"**Email:** {profile.get('email', 'N/A')}")
                st.write(f"**Phone:** {profile.get('phone', 'N/A')}")

            with col2:
                st.write(f"**Skills:** {', '.join(profile.get('skills', []))}")
                st.write(f"**Education:** {', '.join(profile.get('education', []))}")

            # Validation results
            if validation.get("errors"):
                st.error(f"Issues found: {', '.join(validation['errors'])}")
            if validation.get("warnings"):
                st.warning(f"Warnings: {', '.join(validation['warnings'])}")
            if not validation.get("errors"):
                st.success("Resume passed validation ✓")

            # Screening decision
            st.markdown("---")
            st.subheader("Screening Decision")

            col1, col2 = st.columns(2)

            with col1:
                status = "✅ SHORTLIST" if completeness > 70 else "❌ REJECT"
                st.metric("Recommendation", status)

            with col2:
                next_action = "Schedule Interview" if completeness > 70 else "Request Resubmission"
                st.button(next_action)

# Tab 2: Candidate Pool
with tab2:
    st.header("Candidate Pool")

    filter_status = st.multiselect(
        "Filter by Status",
        ["Applied", "Screened", "Shortlisted", "Rejected"],
        default=["Shortlisted"],
    )

    candidates = ats.list_candidates()

    if candidates:
        for candidate in candidates:
            with st.expander(f"👤 {candidate.get('name', 'Unknown')} - Score: {candidate.get('screening_score', 0):.0%}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Email:** {candidate.get('email')}")
                    st.write(f"**Phone:** {candidate.get('phone')}")

                with col2:
                    st.metric("Screening Score", f"{candidate.get('screening_score', 0):.1%}")
                    st.metric("Experience", f"{candidate.get('experience_years', 0)} years")

                with col3:
                    st.metric("Skills", len(candidate.get("skills", [])))
                    st.metric("Match Score", f"{candidate.get('match_score', 0):.1%}")

                st.write(f"**Skills:** {', '.join(candidate.get('skills', []))}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("View Details", key=f"details_{candidate['id']}"):
                        st.write("Opening detailed view...")

                with col2:
                    if st.button("Schedule Interview", key=f"interview_{candidate['id']}"):
                        st.write("Opening interview scheduler...")

                with col3:
                    if st.button("Move to Next Stage", key=f"next_{candidate['id']}"):
                        st.write("Advancing candidate...")
    else:
        st.info("No candidates in pool yet")

# Tab 3: Screening Reports
with tab3:
    st.header("Screening Reports")

    report_type = st.selectbox("Report Type", [
        "Screening Summary",
        "Pass/Fail Analysis",
        "Skills Distribution",
        "Timeline Report",
    ])

    if report_type == "Screening Summary":
        candidates = ats.list_candidates()
        total = len(candidates)
        shortlisted = len([c for c in candidates if c.get("status") == "shortlisted"])
        rejected = len([c for c in candidates if c.get("status") == "rejected"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Screened", total)
        with col2:
            st.metric("Shortlisted", shortlisted)
        with col3:
            st.metric("Rejected", rejected)

        if total > 0:
            pass_rate = (shortlisted / total) * 100
            st.metric("Pass Rate", f"{pass_rate:.1f}%")

    elif report_type == "Skills Distribution":
        all_skills = []
        candidates = ats.list_candidates()
        for candidate in candidates:
            all_skills.extend(candidate.get("skills", []))

        if all_skills:
            skill_counts = {}
            for skill in all_skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

            st.bar_chart(skill_counts)
        else:
            st.info("No skills data available")

    st.markdown("---")
    st.caption("Report generated on demand")
