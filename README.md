# Internship HQ — $0 automatic job importer

This project contains your existing internship dashboard and an automatic importer that uses **public Greenhouse and Lever job feeds**. It does **not** need a paid API, hosting subscription, credit card, or your Gmail password.

## What is working

- Your existing 31 tracker/Gmail records are supplied in a **separate private backup file** (`Internship_HQ_Private_Starter_Backup.json`) outside the public project. Use **Import backup** after opening the dashboard. Your master resume is not included or modified.
- **Not Applied**, **Applied / Reviewing**, **Interviewing / Assessments**, and **Closed** views are separate.
- `scripts/import_jobs.py` checks configured employer feeds for finance, accounting, tax, audit, banking, consulting, risk, insurance and similar Summer 2027/2028 roles.
- GitHub Actions can run the importer twice daily and commit new jobs to `data/jobs.json`.
- Hosted dashboard checks `data/jobs.json` when opened and via **Refresh jobs**. It deduplicates by URL and preserves locally edited statuses.
- The entire app uses free, standard-library Python and static HTML/JS.

## Important limitations

1. **You must enable real employers** in `sources.json` before the importer will find anything. Both sample entries are intentionally disabled, since board tokens should not be guessed. Public feeds cover only employers using supported Greenhouse/Lever boards; this is **not a comprehensive nationwide job search**.
2. The app has **not been deployed** to your GitHub account. A ZIP file cannot schedule itself; the automation starts only after you publish the repository and enable Actions.
3. The dashboard's status edits and notes remain **browser-local**. They are not synced across devices. Use **Export backup** regularly. The hosted repo is public, so **do not commit personal recruiting emails, private notes, or a Google Sheet containing your personal application history**.
4. The public dashboard ships with **no private seed data**. Keep the separate private starter backup off GitHub and import it using the dashboard UI.
5. Scheduled GitHub Actions are best-effort; GitHub may delay or disable inactive schedules. The workflow uses fixed UTC times and shifts by one hour relative to Eastern local time when DST changes. For exact Eastern times, use a timezone-aware scheduler or a higher-frequency UTC workflow with an Eastern-time gate.
6. Third-party free-tier terms can change. This design has no paid services or automatic billing, but no provider can guarantee free availability forever.

## Setup (after addressing privacy)

1. Create a new GitHub repository and upload this project's files, including the `.github/workflows/` folder.
2. In `sources.json`, replace the placeholder board IDs with **verified** public Greenhouse/Lever employer board tokens and set `enabled` to `true`. You can identify Greenhouse board tokens from employer-hosted `boards.greenhouse.io/<token>` or `job-boards.greenhouse.io/<token>` pages, and Lever tokens from `jobs.lever.co/<token>` pages. Confirm permission to use their feeds.
3. Under **Settings → Actions → General**, allow workflows and grant read/write repository contents permissions (if needed). In **Actions**, run **Import internship postings** manually to test. Read the log for errors.
4. Under **Settings → Pages**, publish from the main branch `/ (root)`. Your dashboard will be at `https://YOUR_USERNAME.github.io/YOUR_REPO/` after Pages deployment.
5. Open the hosted dashboard, click **Refresh jobs**, and check **Not Applied**.

## Test locally

```bash
python3 scripts/import_jobs.py
python3 -m http.server 8000
```

Then open `http://localhost:8000` in your browser. The initial importer reports zero new jobs until you configure sources.

## Data safety

Never upload your master resume, private application notes, Gmail tokens, or API secrets to a public repository. The private backup is separate from the deployable ZIP. A private dashboard with true cross-device synchronization requires an authenticated backend; this starter does not pretend to provide one.
