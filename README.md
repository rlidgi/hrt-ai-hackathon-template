# HRT AI Hackathon Template

A GitHub Codespace template for the Hospitality, Recreation, and Tourism (HRT) Applied Research Hackathon. Participants use Claude Code to build a working Streamlit prototype — no coding experience required.

## Getting Started

1. Click **Use this template** → **Open in a codespace**
2. Wait for the environment to set up (~1-2 min)
3. Click the **Claude** (star) icon in the left sidebar
4. Sign in with your Claude Team account
5. Tell Claude what you want to build

## What's Inside

| File | Purpose |
|------|---------|
| `app.py` | Your Streamlit app — Claude writes all code here |
| `CLAUDE.md` | Instructions that guide Claude's behavior |
| `requirements.txt` | Python dependencies (Streamlit, Pandas) |

## Claude Commands

Type these in the Claude Code chat at any time:

| Command | What it does |
|---------|-------------|
| `/checkpoint` | Save your current progress |
| `/back-to-checkpoint` | Restore to your last saved checkpoint |
| `/restart` | Reset everything back to the very beginning |
| `/handoff` | Write a session summary to pick up later |
| `/resume` | Load the previous session summary |

## Running the App

Claude will run the app automatically, but you can also start it manually:

```bash
streamlit run app.py
```

Then open the **Ports** tab in VS Code and click the link next to port `8501`.
