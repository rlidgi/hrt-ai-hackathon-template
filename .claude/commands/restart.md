Reset the project back to the very beginning — the state it was in when the Codespace was first created.

Steps:
1. Run immediately without asking for confirmation:
   - `git reset --hard initial_checkpoint`
   - `git clean -fd`
2. Tell the user: "✅ Project has been reset to the initial state. Fresh start!"

If the `initial_checkpoint` tag does not exist (check with `git tag -l initial_checkpoint`), say:
"❌ Initial checkpoint not found. Please contact the hackathon organizer."
