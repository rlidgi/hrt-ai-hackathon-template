# HRT AI Hackathon Template

A GitHub Codespace template for the Hospitality, Recreation, and Tourism (HRT) Applied Research Hackathon. Participants use Claude Code to build a working Streamlit prototype — no coding experience required.

## Getting Started

1. Click **Code** → **Create Codespace on main**
2. Wait for the environment to set up (1~5min)
3. Click the **Claude** (orange star) icon on the top right corner
4. Sign in with your Claude Team account
5. Tell Claude what you want to build

## What's Inside

| File / Folder | Purpose |
|---------------|---------|
| `app.py` | Your Streamlit app — Claude writes all code here |
| `CLAUDE.md` | Instructions that guide Claude's behavior |
| `requirements.txt` | Python dependencies (Streamlit, Pandas) |
| `data/` | Place your own datasets here (CSV, etc.) |
| `data_ai/` | Claude saves any generated or crawled data here |

## Uploading Data

To upload a file to the `data/` folder:
1. In the left sidebar, right-click the `data/` folder
2. Select **Upload...**
3. Choose your file

CSV files will automatically open as a table when clicked.

## Claude Commands

Type these in the Claude Code chat at any time:

| Command | What it does |
|---------|-------------|
| `/run` | Start the app and show you how to view it |
| `/checkpoint` | Save your current progress |
| `/back-to-checkpoint` | Restore to your last saved checkpoint |
| `/restart` | Reset everything back to the very beginning |
| `/write-readme` | Generate a README based on your current app |
| `/push` | Publish your project to your GitHub portfolio |
| `/handoff` | Write a session summary to pick up later |
| `/resume` | Load the previous session summary |

## Viewing the App

After asking Claude to build something, type `/run` in the chat. Then:
1. Click the **Ports** tab at the bottom of VS Code
2. Click the 🌐 globe icon next to port **8501**
