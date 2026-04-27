Run the Streamlit app and show the user how to view it.

Steps:
1. Check if streamlit is already running: `pgrep -f "streamlit run"` 
   - If already running: skip to step 3
   - If not running: run `streamlit run app.py &` to start it in the background
2. Wait 2 seconds for the server to start
3. Tell the user:

"✅ App is running! To view it:
1. Click the **Ports** tab at the bottom of VS Code
2. Click the 🌐 globe icon next to port **8501**

Or look for a pop-up notification in the bottom-right corner that says 'Open in Browser'."
