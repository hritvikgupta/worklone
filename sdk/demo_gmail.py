"""
Gmail OAuth integration demo — standalone.
Run: python3 demo_gmail.py
"""
import sys, os, asyncio, webbrowser, tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(__file__))
# Set your API key via environment variable or .env file
# export OPENROUTER_API_KEY=sk-or-...
from dotenv import load_dotenv
load_dotenv()

from worklone_employee import Employee
from worklone_employee.integrations import Gmail, InMemoryTokenStore

CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:3000/integrations/callback")
USER_ID       = "demo_user"

token_store = InMemoryTokenStore()

# ── Step 1: open browser ───────────────────────────────────────────────────────
auth_url = Gmail.get_auth_url(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
print("\n" + "="*60)
print("  Gmail OAuth Demo")
print("="*60)
print(f"\nOpening browser — log in and allow access...")
print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
webbrowser.open(auth_url)

# ── Step 2: catch the redirect on localhost:3000 ───────────────────────────────
auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Done! You can close this tab and go back to the terminal.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Error - no code in redirect.</h2>")
    def log_message(self, *args): pass

print("Waiting for Google redirect on http://localhost:3000/integrations/callback ...")
server = HTTPServer(("localhost", 3000), CallbackHandler)
server.timeout = 120
server.handle_request()

if not auth_code:
    print("No auth code received. Make sure http://localhost:3000/callback is in your Google OAuth allowed redirect URIs.")
    sys.exit(1)

# ── Step 3: exchange code → tokens → save to store ───────────────────────────
async def main():
    print(f"\nExchanging code for tokens...")
    tokens = await Gmail.exchange_code(auth_code, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

    print(f"access_token : {tokens['access_token'][:50]}...")
    print(f"refresh_token: {tokens.get('refresh_token', '(not returned)')[:50] if tokens.get('refresh_token') else '(not returned)'}")

    # Save to store — this is YOUR db in production (Postgres, Redis, etc.)
    await token_store.set(USER_ID, "gmail", tokens)
    print(f"\nTokens saved for user='{USER_ID}' — SDK never stores these, they live in YOUR store")

    # ── Step 4: one Gmail instance, wired to employee ─────────────────────────
    gmail = Gmail(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_store=token_store)

    DB = tempfile.mktemp(suffix=".db")
    emp = Employee(
        name="Aria",
        description="An email assistant",
        model="anthropic/claude-haiku-4-5",
        db=DB,
        owner_id=USER_ID,  # flows into context["user_id"] → store.get(USER_ID, "gmail")
    )
    for tool in gmail.all():
        emp.add_tool(tool)
    print(f"\nEmployee ready with {len(gmail.all())} Gmail tools")

    print("\nUSER: Check my Gmail inbox and tell me the subjects of the last 3 emails.")
    print("ARIA: ", end="", flush=True)
    result = await emp._arun("Check my Gmail inbox and tell me the subjects of the last 3 emails.")
    print(result)

    os.remove(DB)
    print("\n" + "="*60)
    print("  Done!")
    print("="*60 + "\n")

asyncio.run(main())
