# Research Desk

A planner for ideas, plans, goals, tasks, deadlines and the calendar, on its
own page at [/desk/](https://s-elim.github.io/desk/). On
[/research-ideas/](https://s-elim.github.io/research-ideas/) only a lock icon
beside the subtitle leads there (it unlocks on hover); the arrow in the desk's
sidebar leads back.

Anyone who opens it can read and edit it; that is the owner's choice. The
Research Resources page itself loads none of it.

```
page (assets/js/desk/*)  --POST-->  Google Apps Script web app (Code.gs), running as you
                                      |-- Google Sheet "Research Desk data": entries, desk tasks,
                                      |   settings, and a revision row for every save
                                      |-- Google Calendar and Google Tasks: read and edit
                                      |-- Drive folder "Research Desk images"
                                      '-- Notion API: dated rows from Research OS, new rows on request
```

Pressing **Refresh** (or `R`, or every five minutes while the desk is open)
re-reads Google Calendar, Google Tasks and Notion. Everything runs on your Google
account's free quotas; there is nothing else to sign up for.

## Set up (about 5 minutes, once)

1. Open <https://script.google.com>, choose **New project**, and name it
   `Research Desk`.
2. Replace everything in `Code.gs` with this folder's [`Code.gs`](Code.gs).
3. **Project Settings** (gear icon) > tick **Show "appsscript.json" manifest file
   in editor**. Back in the editor, open `appsscript.json` and replace it with
   this folder's [`appsscript.json`](appsscript.json). (It switches on Calendar
   and Tasks and sets the time zone to Seoul.)
4. Pick **setup** in the function menu above the code and press **Run**. Google
   asks for permission: Review permissions > your account > Advanced > Go to
   Research Desk > Allow. (Google calls every personal script "unverified".) The
   log ends with `Ready.` and the link to the new Sheet.
5. **Deploy** > **New deployment** > the gear next to "Select type" > **Web app**.
   Execute as **Me**, Who has access **Anyone**, then **Deploy**. Copy the
   **Web app URL**; it ends in `/exec`.
6. Put that URL in `_config.yml` under `desk: endpoint:` (or send it to Claude,
   who will set it and import the old artifact board for you).

### Notion (optional, 2 minutes)

1. <https://www.notion.so/profile/integrations> > **New integration**, type
   Internal, the Research OS workspace, capabilities Read content and Insert
   content. Copy the secret (`ntn_...`).
2. In Notion open **Research OS** > `•••` > **Connections** > add the
   integration. The databases inside inherit the access.
3. In the script: **Project Settings** > **Script properties** > Add
   `NOTION_TOKEN` with the secret. No redeploy needed.

It reads Publication Tracker (Deadline), Opportunities (Deadline), Projects
(Deadline), Career Milestones (Target) and People & Network (Next Follow-up),
and drops rows whose status means finished. JSON in the `NOTION_SOURCES` or
`NOTION_TARGETS` script property replaces those lists (same shape as
`DEFAULT_SOURCES` and `DEFAULT_TARGETS` in `Code.gs`).

### Changing the code later

Paste the new `Code.gs`, then **Deploy** > **Manage deployments** > pencil >
Version **New version** > **Deploy**. The URL stays the same.

## Because anyone can edit

- Changes are metered: 60 a minute and 3,000 a day for everyone together, 60
  images a day. Reading is never limited.
- Every save keeps a revision row; an entry's **History** restores any of them.
  Deletes are soft: **Settings > Recently deleted** brings them back, and a
  delete shows **Undo** for a few seconds.
- Meeting call links (Meet, Zoom, Teams, Webex) are removed from calendar data
  inside the script, so they never reach a browser. Open the event in Google
  Calendar to join.
- One shared snapshot of Calendar, Tasks and Notion is kept for a minute and
  rebuilt after any calendar or task change, so many visitors cost the same as
  one.
- To lock it in seconds: **Script properties** > `DESK_MODE` = `private` and
  `DESK_PASSPHRASE` = a passcode of 4 or more characters. Delete `DESK_MODE` to
  open it again.

## Locking it with a passcode

In private mode the script refuses every read and write without a sign-in
token, so the passcode protects the data itself, not just the page. Each device
asks for the passcode once and stays signed in for 120 days; changing
`DESK_PASSPHRASE` signs every device out. Tokens are signed with a random
secret the script creates for itself (`TOKEN_SECRET`), so a short passcode
cannot be worked out by forging tokens. Ten wrong passcodes in an hour close
sign-in until the hour ends and email you once; devices already signed in keep
working. A 4-digit code is still only 10,000 possibilities, so a longer one is
safer if the email ever arrives.

## Keeping it for twenty years

- The data is a Google Sheet you can open, read and copy. Sheets keeps its own
  version history (File > Version history).
- **Settings > Export JSON** writes everything in the `desk-export-v1` format
  that **Import JSON** reads back; the desk reminds you after 90 days without
  an export. Keep exports beside the quarterly Notion export.
- The page is plain JavaScript with no build step or framework; the backend is
  one file with no dependencies.

## Using it

- **Today**: agenda with a now line, Google Tasks, deadlines from entries,
  Notion and watched conferences, pinned entries and passages.
- **Quick add** understands `today`, `tomorrow`, `fri`, `next mon`, `3/2`,
  `nov 20`, `in 2w`, `2026-11-16`, times `14:00`, `2pm`, `10-11:30`, and
  `#tags`. Task goes to Google Tasks, Event to Google Calendar, Idea to the board.
- Click a **task** to rename, reschedule, add notes or delete it; click an
  **event** to retitle, move, re-time or delete it (read-only calendars just
  show the details).
- **Board**: cards or status lanes, search, filters; the editor has rich text,
  pins, images, history, Send to Notion and Add to Calendar.
- **Calendar**: month, week, day; click an empty slot for a new event.
- Keys: `1`-`4` views, `N` new entry, `T` quick add, `/` search, `R` refresh,
  `[` `]` move the calendar, `Ctrl+S` save.

## Develop and test

```
node --test              # Code.gs against faked Apps Script services, plus the page logic
node dev/server.mjs      # local backend on :8787 with sample Calendar, Tasks and Notion
```

Build the site with `desk.endpoint: http://localhost:8787` in an override config
to drive the real page against it.

## If something goes wrong

The dots at the bottom of the sidebar show each connection; Settings says more.

- **"answered with a page, not data"**: the deployment's access is not *Anyone*,
  or the URL is not the `/exec` one.
- **"Run setup() first"**: step 4 was skipped, or the Sheet was deleted (run it
  again; it makes a new one).
- **Google Tasks warning**: `appsscript.json` from step 3 is missing.
- **Notion "cannot see this database"**: the integration is not connected to
  Research OS.
- **"Too many changes"**: the meter above; it resets within a minute, or at
  midnight UTC for the daily one.
