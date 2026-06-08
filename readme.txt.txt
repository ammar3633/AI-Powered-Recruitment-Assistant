# AI-Powered Recruitment Assistant

A multi-agent recruitment automation system built with Google ADK and MCP servers. Designed to remove the manual bottleneck from hiring pipelines — from resume intake to final candidate ranking.

**Built by:** Mohammed Ammar  
**Stack:** Python, Google ADK, FastMCP, Streamlit

---

## What it does

Hiring teams spend hours screening resumes, coordinating interviews, and ranking candidates. This system automates that entire pipeline using 4 specialized AI agents that communicate asynchronously through a message broker.

---

## Agents

| Agent | Responsibility |
|---|---|
| Resume Screening Agent | Parses resumes, scores completeness and quality |
| Job Matching Agent | Matches candidates to job requirements by skills + experience |
| Interview Coordination Agent | Schedules interviews, manages availability, records feedback |
| Candidate Ranking Agent | Combines all scores and generates final hiring recommendations |

---

## MCP Servers

- **ATS MCP** — manages candidate profiles, job postings, application status
- **Calendar MCP** — handles interview slots, interviewer availability
- **Resume Parser MCP** — extracts structured data from raw resume text

---

## Project Structure
├── agents/                  # 4 ADK agents
├── mcp_servers/             # 3 MCP servers
├── core/                    # Base agent class + inter-agent communication
├── database/                # Data models
├── ui/                      # Streamlit dashboard, screening portal, interview scheduler
├── orchestrator.py          # Ties everything together
└── config.py                # Thresholds, scoring weights, settings
---

## Scoring Logic

**Resume Screening Score**
- Completeness: 40%, Skills: 30%, Experience: 20%, No errors: 10%

**Job Match Score**
- Skill match: 60%, Experience match: 40%

**Final Ranking Score**
- Screening: 30%, Match: 40%, Interview: 30%

---

## Setup

```bash
pip install -r requirements.txt
```

Run the orchestrator:
```bash
python orchestrator.py
```

Launch the dashboard:
```bash
streamlit run ui/dashboard.py
```

---

## Agent Communication Flow