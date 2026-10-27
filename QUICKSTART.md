# Quick Start

Every step from zero to your first job search. For the full guide with screenshots, see [README.md](README.md).

---

## A. Install these first (one time)

1. **Python 3.10 or newer**: https://www.python.org/downloads/
   - Windows: on the first installer screen, tick **"Add python.exe to PATH"**, then click *Install Now*.
2. **Node.js 20 or newer** (LTS): https://nodejs.org/ → download the **LTS** installer, keep the default options.
   It's only used to build the web page.
3. **Git**: https://git-scm.com/downloads (keep the default options).
4. **An OpenAI API key**: https://platform.openai.com/api-keys → *Create new secret key* → copy it
   (starts with `sk-`). Your OpenAI account needs a little credit (Billing).
5. Open a **new** terminal (Windows: *Git Bash*, *Command Prompt* or *PowerShell*; Mac: *Terminal*) and check:

   ```bash
   python --version
   node --version
   git --version
   ```

   - Python must show **3.10 or higher**, Node **v20 or higher**.
   - Windows: if `python` isn't found, try `py --version` and use `py` instead of `python` below.
   - Mac/Linux: use `python3` instead of `python` if needed.

## B. Get the project (one time)

6. Go to the folder where you want the project, for example:

   ```bash
   cd Desktop
   ```

7. Clone the project:

   ```bash
   git clone https://github.com/pattjoshi/playwright-python-job-search.git
   ```

8. Go into the project folder:

   ```bash
   cd playwright-python-job-search
   ```

## C. Set it up (one time)

9. Create a virtual environment (a private Python just for this project):

   ```bash
   python -m venv .venv
   ```

10. Activate it. Use the line for **your** terminal:

   | Terminal | Command |
   |---|---|
   | Windows **Git Bash** | `source .venv/Scripts/activate` |
   | Windows **Command Prompt** | `.venv\Scripts\activate` |
   | Windows **PowerShell** | `.venv\Scripts\Activate.ps1` |
   | **Mac / Linux** | `source .venv/bin/activate` |

   - You should now see **`(.venv)`** at the start of the line.
   - PowerShell says *"running scripts is disabled"*? Run this once, then try again:
     `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

11. Install the backend (Python) packages:

    ```bash
    pip install -r requirements.txt
    ```

12. Install the browser that does the searching:

    ```bash
    playwright install chromium
    ```

13. Build the web page (Node.js; takes a minute the first time):

    ```bash
    cd frontend
    npm install
    npm run build
    cd ..
    ```

14. Create your settings file from the example:

    | Terminal | Command |
    |---|---|
    | Git Bash / Mac / Linux | `cp .env.example .env` |
    | Command Prompt / PowerShell | `copy .env.example .env` |

15. Open **`.env`** in any text editor (Notepad, VS Code) and put your key on this line, then **save**.
    (Or skip this and paste the key later in the app: **Settings → OpenAI key → Save key**.)

    ```ini
    OPENAI_API_KEY=sk-your-key-here
    ```

    - No spaces or quotes around the key.
    - `.env` stays on your computer; it is never uploaded to GitHub.

## D. Run it

16. Start the app (with `(.venv)` active, inside the project folder):

    ```bash
    python -m job_search
    ```

    - Shortcut: **double-click `start_ui.bat`** (Windows) or run `./start_ui.sh` (macOS/Linux) in the
      project folder. It also builds the web page if it isn't built yet.

17. Your browser opens **http://127.0.0.1:8000** by itself. If not, open that address yourself.
    - **First time:** click **Get started** and **create your account** (name, email, password, at least 8 characters).
    - **Next times:** **Sign in** with that email and password.
    - Forgot it? Run `python -m job_search reset-password --email you@example.com` in the project folder.
18. **Keep the terminal window open** while you use the page.

## E. Use it

19. **Upload your resume** (PDF, DOCX or TXT): drag it onto the box or click to choose. Wait a few seconds.
20. **Check "What to look for"**: keywords (from your resume; Enter to add, × to remove), **locations**
    (pick cities and/or *Remote*), **experience** (e.g. 2 to 4 years, or *Any*), **posted within**.
21. **Job sites**: turn LinkedIn / Naukri / Indeed on or off and set **how many jobs to show** from each.
22. **Options**: keep **Show browser** on (lets you solve a "verify you're human" check if a site asks).
23. Click **Start search**. Watch the progress; click **Stop search** to cancel.
24. **Results**: best matches first, with score, matching / missing skills and a reason.
    - **View job ↗** opens it on the site (apply there).
    - **✓ Mark applied** / **Hide** remove it from future results.
25. **My jobs** (top right): your applied and hidden jobs, plus the **search history**.
26. **Daily search** (optional): pick a time and days → **Save daily search**. It runs automatically
    even when the page is closed and opens the report when done.
27. **Reload or restart anytime**: the page keeps your resume and results. Click **Clear** (top right)
    to remove them.

## F. Stop it

28. Go to the terminal window and press **Ctrl + C**.

## G. Next time

29. Open a terminal, go to the project folder, activate the environment, start the app:

    ```bash
    cd Desktop/playwright-python-job-search
    source .venv/Scripts/activate        # use your terminal's command from step 10
    python -m job_search
    ```

    Or just double-click **`start_ui.bat`** (Windows).

## H. Get the latest version

30. In the project folder, with `(.venv)` active:

    ```bash
    git pull
    pip install -r requirements.txt
    cd frontend && npm install && npm run build && cd ..
    ```

    - Coming from an older version (before the `backend/` and `frontend/` folders)? These same commands
      are all you need. Your applied/hidden jobs, search history and daily search are kept.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `python` / `pip` not found | Reinstall Python with **"Add python.exe to PATH"** ticked, open a new terminal. Or use `py`. |
| `No module named job_search` | The environment isn't active, or step 11 was skipped: activate it (step 10), then `pip install -r requirements.txt`. |
| Page says **"The web page isn't built yet"** | Run step 13 (`npm install` and `npm run build` in the `frontend` folder), then reload. |
| `npm` not found | Install Node.js (step 2), then open a **new** terminal. |
| `No module named fastapi` / `playwright` | The environment isn't active (no `(.venv)`): run step 10, then step 11. |
| Browser error on start ("Executable doesn't exist") | Run step 12: `playwright install chromium`. |
| Page says **Add your OpenAI key first** | Open **Settings → OpenAI key** and save it, or check step 15 and restart the app (Ctrl+C, step 16). |
| Forgot your password | In the project folder (with `(.venv)` active): `python -m job_search reset-password --email you@example.com`. |
| **Address already in use** / port 8000 busy | The app is already running in another window, or start it on another port: `python -m job_search --port 8001`. |
| A site finds **0 jobs** | Look at the number line under the progress bar and the yellow hint; widen cities, experience or *Posted within*. Click **Show log** for details. |
| "Verify you're human" on Naukri / Indeed | Keep **Show browser** on and solve it in the browser window. |
