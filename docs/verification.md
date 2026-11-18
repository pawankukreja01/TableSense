# Verification and limits
The build was checked with Python 3.12, Django 5.2, SQLite, a local PostgreSQL 18.6 instance and headless Chromium. The 21 Django tests passed against both database engines. The Vue TypeScript/Vite production build and Vitest currency-format check passed. The seeded browser walkthrough exercised the real HTTP API, two browser tabs, an 800×1280 guest tablet, landscape guest display, a phone-width staff floor, Wi-Fi loss simulation/recovery, separate requested/fulfilled records, the manager journal and session reset.

To repeat on a local checkout:

    python -m pip install -r requirements.txt
    python manage.py test
    cd frontend
    npm ci
    npm test
    npm run build

For the browser check, start a **fresh private demo database**, install the optional Playwright Python package and its Chromium runtime, then run:

    python -m pip install playwright
    python -m playwright install chromium
    python qa/browser_demo.py

Set TABLESENSE_URL to override http://127.0.0.1:8080 and CHROMIUM to use a specific Chromium binary. The walkthrough creates a device pairing, session and outcomes. Use a disposable database for repeated runs. With SQLite, set SQLITE_PATH to a new path before migrating, seeding and launching. To run backend tests against PostgreSQL, configure POSTGRES_HOST and POSTGRES_PASSWORD with a tablesense account permitted to create a temporary test database.

## Limits and next steps
- Docker Compose is supplied. Docker was unavailable in the build environment; the container build and bundled PostgreSQL 16 image were not executed there. The app and database migrations were exercised directly against PostgreSQL and SQLite.
- Tablet styling and connectivity were exercised in Chromium emulation. Physical Android/iPad kiosk lockdown, Safari behavior, full-shift battery life, mounting and restaurant Wi-Fi load need on-site acceptance.
- True POS connectivity, verified revenue, verified waste prevention and incremental contribution require operational evidence. The mock POS is a test adapter. Staff-confirmed additions stay labeled as manual. The pilot does not estimate profit from impressions.
- Anonymous feedback is recorded in issue notes. Cohort eligibility, staff workload and event logs are available; control-group item-level sales reconciliation and confidence intervals take place outside this prototype.
- Menu images are bundled demonstration photos, placeholders or manager-supplied URLs. Use actual restaurant images and recipe information for service. One venue currency/timezone is provisioned (GBP, Europe/London). One user belongs to one venue.
- Server-sent notifications and polling are suitable for a small pilot. Rehearse production load, proxy configuration, retention and disaster recovery before going live. Run a physical pilot before making a commercial performance claim.
