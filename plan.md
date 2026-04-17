1. Modify `ChatView.tsx` to maintain a list of `tabs`.
2. A tab is `{ id: string, employeeId: string, sessionId: string }`.
3. State:
   - `tabs`: `Tab[]`
   - `activeTabId`: `string`
4. On load, we still load `employees`. If there are employees but no tabs, we can maybe fetch the last session of the first employee and open it, or just show a welcome screen. The current behavior loads the first session of the first employee. We can keep that: initialize one tab with it.
5. `handleStartNewSession(employeeId)`:
   - Creates a new session.
   - Appends `{ id: newSession.id, employeeId, sessionId: newSession.id }` to `tabs`.
   - `setActiveTabId(newSession.id)`.
   - Fetches messages (which will be empty).
6. "History" dropdown inside the chat header:
   - Lists sessions for `activeEmployeeId`.
   - On click session `s`:
     - If `tabs` contains `s.id`, set `activeTabId(s.id)`.
     - Else, append `{ id: s.id, employeeId, sessionId: s.id }` to `tabs`, and set `activeTabId(s.id)`.
     - Fetch messages for `s.id`.
7. Chat Panel:
   - Use `ChatProvider`, `ChatHeader`, `ChatMessages`, `ChatComposer`.
   - Remove `FullMessenger` because it hardcodes the sidebar.
   - Top of the chat view: A tab bar.

Tab Bar UI:
- A flex container, `border-b`, `bg-[var(--chat-bg-sidebar)]` or similar.
- Each tab: `flex items-center gap-2 px-4 py-2 border-r ...`, active tab has different background (e.g., `bg-[var(--chat-bg-main)]`) and maybe a top border line.
- Each tab has a title: Employee Name, and maybe a close button (`X`).

Let's refine the tab title. The user said "browser style tab".
Tab title should probably be `Employee Name - Session Title`.
And an `X` to close it.

Let's write a targeted `replace` for `ChatView.tsx`.
Wait, replacing `ChatView.tsx` entirely with `write_file` might be easier since the layout changes significantly.
Let's see the current `ChatView.tsx` code. It's about 430 lines.
