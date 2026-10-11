# Research Desk

A private planner for ideas, plans, goals, tasks, deadlines and the calendar,
living at the top of [/research-ideas/](https://s-elim.github.io/research-ideas/)
and on its own at [/desk/](https://s-elim.github.io/desk/). Visitors see neither:
the page ships an empty, hidden section, and the desk's scripts load only in a
browser that unlocked it once or opens `#desk` / `/desk/`.

```
browser (assets/js/desk/*)  --bearer token-->  Cloudflare Worker (src/worker.js)
                                                 |-- D1: entries, desk tasks, settings, images, every revision
                                                 |-- Notion API: dated rows from Research OS, new rows on request
                                                 '-- Apps Script bridge (bridge/Code.gs), running as you:
                                                      Google Calendar events + Google Tasks, read and write
```

Pressing **Refresh** (or `R`, or every five minutes while the tab is visible)
re-reads Google Calendar, Google Tasks and Notion in one request.

| Piece | Free allowance (check the vendor's page) |
| --- | --- |
| Cloudflare Workers | 100,000 requests per day |
| Cloudflare D1 | 5 GB storage, 5 million rows read and 100,000 written per day |
| Notion internal integration | free on every plan |
| Google Apps Script | consumer quotas, far above one person's use |

## Set up (about 25 minutes, once)

### 1. Database and Worker (Cloudflare dashboard)

1. **D1.** Workers & Pages > D1 SQL Database > Create, name it `desk`. No tables
   to create; the Worker makes them on first use.
2. **Worker.** Workers & Pages > Create > Create Worker, name it
   **`homepage-desk`** (the site expects
   `https://homepage-desk.selim-sarowar12.workers.dev`; another name means
   changing `desk.endpoint` in `_config.yml`). Deploy, then **Edit code**, replace
   everything with `src/worker.js`, Deploy.
3. **Binding.** Worker > Settings > Bindings > Add > D1 database: variable name
   `DB`, database `desk`.
4. **Variables.** Worker > Settings > Variables and secrets:
   - `ALLOWED_ORIGINS`, Text: `https://s-elim.github.io`
   - `DESK_PASSPHRASE`, Secret: a long passphrase (12+ characters; four or five
     random words is good). Changing it later signs out every device.

   Deploy again. `https://homepage-desk.selim-sarowar12.workers.dev/health`
   should now show `"db":true,"passphrase":true`.
5. Open <https://s-elim.github.io/desk/>, unlock with the passphrase, and let the
   browser's password manager save it.

The desk works from here on: board, desk tasks, conference deadlines, export.
Steps 2 and 3 connect the outside services; each is optional.

### 2. Notion (Research OS)

1. <https://www.notion.so/profile/integrations> > New integration, type
   **Internal**, workspace of Research OS. Capabilities: Read content, Insert
   content. Copy the **Internal Integration Secret** (`ntn_...`).
2. In Notion open **Research OS** > `•••` > Connections > add the integration.
   Child databases inherit the access.
3. Worker > Variables and secrets: `NOTION_TOKEN`, Secret, the `ntn_...` value.

Read by default (date column in brackets): Publication Tracker (Deadline),
Opportunities (Deadline), Projects (Deadline), Career Milestones (Target),
People & Network (Next Follow-up). Rows whose status means finished (Accepted,
Shipped, Done, Applied, ...) drop off the deadline list. To change the list
without touching code, set `NOTION_SOURCES` to JSON in the same shape as
`DEFAULT_SOURCES` in `src/worker.js`; `NOTION_TARGETS` does the same for the
databases an entry can be sent to (Ideas, Research Roadmap, Career Milestones).

### 3. Google Calendar and Google Tasks

1. <https://script.google.com> > New project, name it `desk bridge`.
2. Replace `Code.gs` with `bridge/Code.gs`.
3. Project Settings (gear) > tick **Show "appsscript.json" manifest file**, open
   it in the editor and replace it with `bridge/appsscript.json` (this turns on
   the Calendar and Tasks services and sets your time zone; change
   `Asia/Seoul` if needed).
4. Choose `setup` in the function menu, press **Run**, and allow access
   (Google shows "unverified app" for your own scripts: Advanced > Go to desk
   bridge). The execution log prints `DESK_SECRET = ...`; copy it.
5. Deploy > New deployment > type **Web app**; Execute as **Me**; Who has access
   **Anyone**. Copy the URL ending in `/exec`.
6. Worker > Variables and secrets: `GOOGLE_BRIDGE_URL` (Secret, the `/exec` URL)
   and `GOOGLE_BRIDGE_SECRET` (Secret, the printed secret).

"Anyone" is required because the Worker calls the script without a Google
login; the script refuses every request that lacks the 64-character secret.
`rotateSecret()` issues a new one. After editing `Code.gs`, use Deploy > Manage
deployments > Edit > New version, so the URL stays the same.

Only calendars ticked as visible in Google Calendar are read, and events you
declined are skipped. Tasks: all open ones, plus those finished in the window.

### 4. Bring over the old artifact board

Settings (gear) > **Import JSON** and pick
`desk_migration/research_desk_import_2026_10_11.json` (kept outside this public
repository). It holds the five entries from the claude.ai artifact, formatting
and the pinned plan included, plus the watched conferences and the Research OS
link. Importing twice changes nothing.

## Using it

- **Today**: agenda with a now line, Google Tasks (or desk tasks before Google is
  connected), deadlines from entries, Notion and watched conferences, pinned
  entries and pinned passages.
- **Quick add** understands `today`, `tomorrow`, `fri`, `next mon`, `3/2`,
  `nov 20`, `in 2w`, `2026-11-16`, times `14:00`, `2pm`, `10-11:30`, and
  `#tags`. Task goes to Google Tasks, Event to Google Calendar (or a pre-filled
  Google Calendar tab when the bridge is not set up), Idea to the board.
- **Board**: cards or status lanes (drag between lanes), search, filters. The
  editor has rich text, colour and highlight, pinned passages, images, history
  with restore, Send to Notion (fields read live from the database), and Add to
  Calendar.
- **Calendar**: month, week, day; events, tasks and deadlines as layers; click an
  empty slot for a new event.
- Keys: `1`-`4` views, `N` new entry, `T` quick add, `/` search, `R` refresh,
  `F` full screen, `[` `]` move the calendar, `Ctrl+S` save in the editor.

## Keeping it for twenty years

- Every save writes a revision row; the editor's **History** restores any of
  them. Deletes are soft.
- D1 Time Travel restores the whole database to any minute of the last 7 days
  on the free plan (30 on Workers Paid): D1 > desk > Time Travel.
- **Export JSON** (Settings) writes everything, images included, in the
  `desk-export-v1` format that **Import JSON** reads back. The desk reminds you
  when the last export is older than 90 days. Keep exports beside the quarterly
  Notion export.
- The client is plain JavaScript with no build step or framework; the Worker is
  one file with no dependencies; data is JSON in SQLite. Moving to another host
  means porting about 650 lines of `src/worker.js`, not the data.

## Develop and test

```
node --test                          # Worker, bridge (in a sandbox) and desk logic
MOCK=1 node dev/server.mjs           # local Worker on :8787 with sample Google + Notion
```

The dev server accepts `http://localhost:4000`; build the site with
`desk.endpoint: http://localhost:8787` in an override config to drive the real
UI against it. Passphrase: `local desk passphrase`.

## If something goes wrong

The dots in the sidebar footer show each connection; hover for the reason, or
open Settings.

- **"server at ... is not answering"**: the Worker is not deployed under that
  name, or `ALLOWED_ORIGINS` does not include the page's origin.
- **"DESK_PASSPHRASE is missing"** or **"bind a D1 database"**: step 1.4 or 1.3.
- **"Too many wrong attempts"**: eight failures from one address lock it for 15
  minutes.
- **Notion: "cannot see this database"**: the integration is not connected to
  Research OS (step 2.2).
- **Google: "answered with a page, not data"**: the web app is not deployed with
  access *Anyone*, or the URL is not the `/exec` one.
- **Google: "Wrong or missing bridge secret"**: `GOOGLE_BRIDGE_SECRET` differs
  from the script's `DESK_SECRET`.
