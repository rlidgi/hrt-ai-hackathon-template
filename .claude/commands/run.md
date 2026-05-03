Run the Streamlit app and give the user a direct, clickable link.

Steps:
1. Kill any existing streamlit process: `pkill -f "streamlit run" 2>/dev/null; sleep 1`
2. Start streamlit bound to all interfaces (required for Codespace port forwarding):
   ```
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > /tmp/streamlit.log 2>&1 &
   ```
3. Wait for the server to be ready by polling the port:
   ```
   for i in {1..20}; do curl -s http://localhost:8501 >/dev/null && break; sleep 1; done
   ```
4. Determine the URL:
   - If `$CODESPACE_NAME` is set: `https://${CODESPACE_NAME}-8501.app.github.dev`
   - Otherwise: `http://localhost:8501`
5. Tell the user — print the URL on its own line so VS Code makes it clickable:

```
✅ Your app is running. Click the link below to open it:

<URL>
```

If the curl polling never succeeds, tail `/tmp/streamlit.log` and show the user the error.

Do NOT tell the user about ports, sidebars, or globe icons. Just give the link.
