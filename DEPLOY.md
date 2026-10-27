# Put Applications and Notes online (Vercel)

The online version lets you open **Applications**, **Notes**, the dashboard and Settings from any device.
**Searching stays on your computer**: it opens a real browser and runs for minutes, which Vercel can't do.

What you need: a free [Vercel](https://vercel.com) account, a free [Neon](https://neon.tech) Postgres database, and
this repository on your GitHub. About 15 minutes.

## 1. Create the database (Neon, free)

1. Sign in at [neon.tech](https://neon.tech) → **New project** (pick a region near you, e.g. Singapore or Mumbai).
2. On the project page, **Connect** → copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   This is your **DATABASE_URL**. Keep it private: it's the key to your data.

(Supabase works too: Project settings → Database → Connection string, "URI".)

## 2. Make a setup code

The first person to open a fresh install creates the account. Online, that could be a stranger, so creating it needs a
**setup code** only you know. Make one, any long random text, for example in a terminal:

```bash
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

## 3. Deploy on Vercel

1. [vercel.com/new](https://vercel.com/new) → **Import** your `playwright-python-job-search` repository.
2. Leave **Framework Preset: Other** and **Root Directory** as the repository root (`vercel.json` sets the rest).
3. **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `SETUP_CODE` | the code from step 2 |
   | `APP_SECRET` | (optional) another long random text |

4. **Deploy**. Vercel deploys the branch set as **Production Branch** (Settings → Git; `main` by default, change it to
   `develop` if that's where your latest code is).

## 4. Copy your data (optional, before signing up)

To take your applications, notes and job history (and your account, same email and password) online, run this once
on your computer, in the project folder with the virtual environment active:

```bash
python -m job_search copy-to-cloud --to "postgresql://user:password@ep-xxxx.neon.tech/neondb?sslmode=require"
```

It refuses to run if the online database already has an account, so nothing is ever mixed or duplicated.

## 5. Open it

Open your Vercel address (e.g. `https://playwright-python-job-search.vercel.app`):

- **Copied your data?** Sign in with your usual email and password.
- **Starting fresh?** Create your account and type the setup code.

Using your own domain? Add it in Vercel (Settings → Domains) **and** to the `ALLOWED_HOSTS` environment variable
(e.g. `jobs.example.com`), then redeploy. Vercel's own `*.vercel.app` addresses are allowed automatically.

## Good to know

- **Search, resume reading, the daily search and the saved OpenAI key** only work in the app on your computer. Online,
  the Search page says so, and those parts are hidden.
- The app on your computer and the online one have **separate data**: the computer keeps using `data/history.sqlite3`.
  `copy-to-cloud` is a one-time copy, not a sync.
- Neon's free database sleeps when unused, so the first page after a while can take a few seconds.
- Security online: HTTPS-only sign-in cookie, the setup code, the same password hashing and Origin checks as on your
  computer. The limit on wrong passwords is kept in memory, per Vercel instance, so it's softer online: use a long password.
- A build or start error on Vercel? Open the deployment's **Logs** and send the red lines.
