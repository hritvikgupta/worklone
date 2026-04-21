"""
End-to-end SDK demo — tools, session persistence, evolution.
"""
import sys, os, time, tempfile

# Remove current dir from path so we import from PyPI, not local folder
sys.path = [p for p in sys.path if not p.endswith('/sdk') and p != '']


os.environ["OPENROUTER_API_KEY"] = "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"

DB = tempfile.mktemp(suffix=".db")

print("\n" + "=" * 60)
print("  worklone-employee SDK  —  Live End-to-End Demo")
print("=" * 60)

from worklone_employee import Employee, BaseTool, ToolResult
from worklone_employee.db.store import EmployeeStore
from worklone_employee.evolution.evolution_store import EvolutionStore

# ── 1. Create employee with session ───────────────────────────────────────────
SESSION_ID = "demo-session-001"

emp = Employee(
    name="Aria",
    description="A smart research assistant",
    model="anthropic/claude-haiku-4-5",
    system_prompt="You are Aria, a sharp research assistant. Always use available tools before answering. Be concise.",
    db=DB,
    session_id=SESSION_ID,
)

store = EmployeeStore(DB)
store.create_chat_session(user_id="sdk_user", employee_id=emp._employee_id, title="Demo Session", model="anthropic/claude-haiku-4-5")
import sqlite3; conn = sqlite3.connect(DB); conn.execute("UPDATE chat_sessions SET id=? WHERE employee_id=?", (SESSION_ID, emp._employee_id)); conn.commit(); conn.close()

print(f"\n✓  Employee: {emp._employee_id}  Session: {SESSION_ID}")

@emp.tool(description="Look up the current price of a stock ticker symbol")
def get_stock_price(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "GOOGL": "$175.20", "MSFT": "$415.50", "NVDA": "$875.00", "TSLA": "$245.80", "AMZN": "$198.40"}
    return prices.get(ticker.upper(), f"No data for {ticker}")

@emp.tool(description="Calculate compound interest given principal, rate, and years")
def compound_interest(principal: float, rate: float, years: int) -> str:
    result = principal * (1 + rate / 100) ** years
    return f"${result:,.2f} after {years} years (${principal:,.2f} @ {rate}% annually)"

emp.use_tools(["web_search"])
emp.enable_evolution()
print("✓  Tools + evolution enabled\n")


# ── 2. Run 8+ turns with tool calls to trigger evolution ──────────────────────
print("── Running 8 turns to trigger evolution ────────────────────────")
tasks = [
    "Search the web for the latest news about NVIDIA stock today.",
    "What is the price of NVDA?",
    "What is the price of AAPL?",
    "What is the price of MSFT?",
    "What is the price of TSLA?",
    "What is the price of AMZN?",
    "If I invest $5,000 in NVDA at 20% for 3 years, what do I get?",
    "If I invest $10,000 in AAPL at 12% for 5 years, what do I get?",
    "If I invest $20,000 in MSFT at 15% for 10 years, what do I get?",
    "Give me a one-sentence summary of all the stocks and investments we discussed.",
]

for i, task in enumerate(tasks, 1):
    print(f"\nTurn {i} — USER: {task}")
    print("ARIA: ", end="", flush=True)
    print(emp.run(task))

print(f"\n── DB: {len(store.get_chat_history(SESSION_ID))} messages saved ─────────────────────")


# ── 3. Wait for background evolution threads to finish ────────────────────────
print("\n── Waiting 8s for evolution background threads... ──────────────")
time.sleep(8)


# ── 4. Check evolution store ──────────────────────────────────────────────────
evo = EvolutionStore(DB)
memory = evo.get_user_memory(emp._employee_id, "sdk_user")
skills = evo.list_skills_full(emp._employee_id, emp._owner_id)

print("\n── EVOLUTION RESULTS ────────────────────────────────────────────")
print(f"\n  USER MEMORY ({len(memory)} chars):")
print(f"  {memory if memory else '(none written yet)'}")
print(f"\n  LEARNED SKILLS ({len(skills)}):")
for s in skills:
    print(f"  • [{s['title']}] v{s['version']} — {s['description']}")
    print(f"    {s['content'][:200]}...")


# ── 5. Simulate restart — new Employee, same session, check memory injected ───
print("\n── RESTART SIMULATION ───────────────────────────────────────────")
emp2 = Employee(name="Aria", model="anthropic/claude-haiku-4-5", db=DB, session_id=SESSION_ID)

@emp2.tool(description="Look up the current price of a stock ticker symbol")
def get_stock_price2(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "GOOGL": "$175.20", "MSFT": "$415.50", "NVDA": "$875.00", "TSLA": "$245.80", "AMZN": "$198.40"}
    return prices.get(ticker.upper(), f"No data for {ticker}")

@emp2.tool(description="Calculate compound interest given principal, rate, and years")
def compound_interest2(principal: float, rate: float, years: int) -> str:
    result = principal * (1 + rate / 100) ** years
    return f"${result:,.2f} after {years} years (${principal:,.2f} @ {rate}% annually)"

print("USER: Which stocks did we look up earlier?")
print("ARIA: ", end="", flush=True)
print(emp2.run("Which stocks did we look up earlier?"))


# ── 6. Human-in-the-loop approval demo ───────────────────────────────────────
print("\n── HUMAN-IN-LOOP DEMO ───────────────────────────────────────────")

emp3 = Employee(
    name="Aria",
    description="A research assistant",
    model="anthropic/claude-sonnet-4-5",
    system_prompt=(
        "You are Aria, a research assistant.\n\n"
        "STRICT RULE: Any request with more than one step MUST start with manage_tasks (create_plan) "
        "followed immediately by ask_user to show the plan and wait for approval. "
        "You are FORBIDDEN from calling any execution tool (web_search, get_stock_price, etc.) "
        "until the user has approved the plan. No exceptions."
    ),
    db=DB,
    owner_id="sdk_user",
)
emp3.use_tools(["web_search"])

@emp3.tool(description="Look up the current price of a stock ticker symbol")
def get_stock_price3(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "GOOGL": "$175.20", "MSFT": "$415.50", "NVDA": "$875.00", "TSLA": "$245.80", "AMZN": "$198.40"}
    return prices.get(ticker.upper(), f"No data for {ticker}")

approval_fired = False

@emp3.on_approval_needed
def handle_approval(event):
    global approval_fired
    approval_fired = True
    print(f"\n  ✋ AGENT PAUSED — approval needed")
    print(f"  Message : {event.get('message', '')[:200]}")
    plan = event.get("plan") or {}
    tasks = plan.get("tasks", [])
    if tasks:
        print(f"  Plan ({len(tasks)} tasks):")
        for t in tasks:
            print(f"    • {t.get('title', t.get('task_title', ''))}")
    print(f"  → Auto-approving for demo")
    return {"approved": True, "message": "Approved by demo"}

print("\nUSER: Search the web for NVIDIA news, then look up the stock price, then create a short investment summary.")
print("ARIA: ", end="", flush=True)
result = emp3.run("Search the web for NVIDIA news, then look up the NVDA stock price, then create a short investment summary combining both.")
print(result)
print(f"\n  approval_fired={approval_fired}")

# ── 7. Gmail tool via decorator ──────────────────────────────────────────────
print("\n── GMAIL DECORATOR TEST ─────────────────────────────────────────")

emp4 = Employee(
    name="Aria",
    description="An email assistant",
    model="anthropic/claude-haiku-4-5",
    db=DB,
    owner_id="sdk_user",
)

INBOX = [
    {"id": "msg_001", "from": "alice@example.com", "subject": "Q1 Report", "snippet": "Please review the Q1 numbers attached."},
    {"id": "msg_002", "from": "bob@example.com",   "subject": "Team lunch Friday", "snippet": "Are you free Friday at noon?"},
    {"id": "msg_003", "from": "carol@example.com", "subject": "Invoice #4421", "snippet": "Invoice for March services is attached."},
]
SENT = []

@emp4.tool(description="List unread emails from inbox. Returns a list of emails with id, from, subject, snippet.")
def gmail_list_inbox() -> str:
    return str(INBOX)

@emp4.tool(description="Send an email. Args: to (email address), subject, body.")
def gmail_send(to: str, subject: str, body: str) -> str:
    SENT.append({"to": to, "subject": subject, "body": body})
    return f"Email sent to {to} with subject '{subject}'"

print("\nUSER: Check my inbox and reply to the invoice email saying I'll process it tomorrow.")
print("ARIA: ", end="", flush=True)
result4 = emp4.run("Check my inbox and reply to the invoice email saying I'll process it tomorrow.")
print(result4)
print(f"\n  Emails sent: {len(SENT)}")
if SENT:
    print(f"  → To: {SENT[0]['to']} | Subject: {SENT[0]['subject']}")
    print(f"  → Body: {SENT[0]['body'][:100]}")

# ── 8. Gmail OAuth flow demo ──────────────────────────────────────────────────
print("\n── GMAIL OAUTH INTEGRATION DEMO ─────────────────────────────────")

import asyncio
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from worklone_employee.integrations import Gmail, InMemoryTokenStore

CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:3000/callback")
USER_ID       = "demo_user"

# In-memory store (swap with your Postgres/Redis store in production)
token_store = InMemoryTokenStore()

# Step 1 — Generate auth URL and open browser
auth_url = Gmail.get_auth_url(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
print(f"\nOpening browser for Gmail OAuth...")
print(f"URL: {auth_url}\n")
webbrowser.open(auth_url)

# Step 2 — Spin up a local server to catch the redirect and grab the code
auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Auth complete! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Error: no code received.</h2>")
    def log_message(self, *args): pass  # silence server logs

print("Waiting for Google to redirect back (you have 60s to log in)...")
server = HTTPServer(("localhost", 3000), CallbackHandler)
server.timeout = 120
server.handle_request()  # blocks until one request comes in

if not auth_code:
    print("No auth code received — skipping Gmail demo.")
else:
    # Step 3 — Exchange code for tokens
    async def run_gmail_demo():
        print(f"\nExchanging code for tokens...")
        tokens = await Gmail.exchange_code(auth_code, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
        print(f"access_token : {tokens['access_token'][:40]}...")
        print(f"refresh_token: {tokens.get('refresh_token', '(none)')[:40]}...")

        # Step 4 — Save tokens to store (keyed by user_id — SDK never touches them again)
        await token_store.set(USER_ID, "gmail", tokens)
        print(f"\nTokens saved to store for user '{USER_ID}'")

        # Step 5 — Create ONE Gmail instance that serves this user
        gmail = Gmail(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_store=token_store)

        # Step 6 — Wire to employee and run
        # owner_id becomes user_id in tool context — this is how the store lookup works
        emp5 = Employee(
            name="Aria",
            description="An email assistant",
            model="anthropic/claude-haiku-4-5",
            db=DB,
            owner_id=USER_ID,  # ← this flows into context["user_id"] for every tool call
        )
        emp5.add_tools(gmail.all())

        print(f"\nUSER: Check my Gmail inbox and tell me the subject of the latest email.")
        print("ARIA: ", end="", flush=True)
        result = emp5.run("Check my Gmail inbox and tell me the subject of the latest email.")
        print(result)

    asyncio.run(run_gmail_demo())

# ── Cleanup ────────────────────────────────────────────────────────────────────
os.remove(DB)
print("\n✓  Demo complete.\n" + "=" * 60 + "\n")
