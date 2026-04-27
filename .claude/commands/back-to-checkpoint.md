Restore the project to the last saved checkpoint.

Steps:
1. Check if the `checkpoint` tag exists: `git tag -l checkpoint`
   - If it does NOT exist: say "❌ No checkpoint found yet. Use /checkpoint to save your current state first." and stop.
2. Run immediately without asking for confirmation:
   - `git reset --hard checkpoint`
   - `git clean -fd`
3. Tell the user: "✅ Restored to your last checkpoint!"
