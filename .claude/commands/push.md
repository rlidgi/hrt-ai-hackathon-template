Save and publish the student's work to their own GitHub repository.

Steps:
1. Run `git add -A`
2. Check if there is anything staged: `git diff --cached --quiet`
   - If there ARE changes: run `git commit -m "hackathon project"`
   - If nothing to commit: skip the commit step
3. Run `git push 2>&1` and check the output:
   - If push succeeds: tell the user the repo URL and go to step 5
   - If it fails with "no upstream" or "not found": the Codespace is not yet linked to GitHub — go to step 4
4. If not yet published:
   - Tell the user: "Let's publish this to your GitHub account."
   - Instruct them to: click the **Source Control** icon (branch icon) in the left sidebar → click **Publish Branch** → sign in if prompted → choose **Public** so it appears on their portfolio
5. Tell the user:
"✅ Your project is saved to GitHub! You can find it at github.com/YOUR_USERNAME/REPO_NAME.
Share this link as part of your portfolio."
