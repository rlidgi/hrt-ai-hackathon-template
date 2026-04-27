Save the current state of the project as a checkpoint.

Run these bash commands in order:
1. `git add -A`
2. Check if there is anything staged: `git diff --cached --quiet`
   - If there ARE changes: run `git commit -m "checkpoint"`
   - If nothing to commit: skip the commit step
3. `git tag -f checkpoint HEAD`

After completing, tell the user:
"✅ Checkpoint saved! You can return here anytime with /back-to-checkpoint"

Important: Never modify or delete the `initial_checkpoint` tag.
