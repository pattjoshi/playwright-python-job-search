# Job Search Auto-apply (Chrome extension)

Applies to your queued **Easy Apply** jobs on Naukri, LinkedIn and Indeed **in your own Chrome**, where you're
already signed in. It works with the Job Search app running on your computer: the app decides *what* to apply to
(the queue, your Answer Bank, dry run, daily limits); the extension does the clicking in a Chrome tab.

## Set up (once)

1. Start the app (`python -m job_search`).
2. In Chrome open `chrome://extensions`, turn on **Developer mode**, press **Load unpacked** and pick this
   `extension` folder.
3. In the app go to **Auto-apply → Chrome extension → Connect extension** and copy the key.
4. Click the extension's icon (pin it from the puzzle-piece menu), paste the key, press **Save and test**.
   It shows "Connected as …", how many jobs are waiting and whether dry run is on.

## Use

- Turn on the boards you want in **Auto-apply → Settings → Job boards** (no Sign in or passwords needed with the
  extension: it uses your Chrome's own logins).
- Run a search; matching Easy Apply jobs are queued. Click the extension's icon and press **Start**.
- It opens a tab and applies to one job at a time, waiting 30–50 seconds between jobs. Leave that tab alone while it
  works (you can use other tabs and windows). Press **Stop** any time.
- Results, screenshots and answers show on the Auto-apply page as usual; submitted jobs go to Applications.
- Questions your Answer Bank can't answer stop that job and appear under **Answer Bank → Needs answer**.
- **Dry run** (on until you turn it off in the app) fills everything but never submits.

## How it works

- `background.js` (service worker): asks the app for the next job (`/api/extension/next`), opens it, injects the
  page scripts, takes a screenshot and reports the result. Talks to the app with the key (`lib/api.js`).
- `content/fields.js` reads and fills form fields, `content/fill.js` decides each answer (resume upload, AI cover
  letter, names, else the Answer Bank), `content/boards.js` runs LinkedIn / Indeed / Naukri Easy Apply and
  `content/naukri-chat.js` answers Naukri's chat questions.
- Chrome asks for access to all sites because screenshots need it, but the extension only opens, fills and captures
  pages on the job's own board (LinkedIn, Naukri, Indeed over https) or the app on your computer (`allowedPage()` in
  `background.js`): a job link pointing anywhere else is refused, and so is a page that redirected away from the board. It only talks to the app
  address you set (default `http://127.0.0.1:8000`). After updating, press **Reload** on `chrome://extensions`.

Job boards don't allow automated applying; keep the daily limits low.
