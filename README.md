# TableSense
A working restaurant upselling pilot for a guest tablet, staff phone and manager browser. The guest sees up to two approved meal pairings, can dismiss them and can ask the waiter verbally. Staff take every actual order through the restaurant’s existing process.

## Start the demo
Install Docker Desktop or Docker Engine with Compose. Open a terminal in this extracted folder and run:

    docker compose up --build

Visit **http://localhost:8080**. Choose **Enter manager demo** or **Enter staff demo**. The first launch seeds Demo Bistro, eight tables, fifteen items, and eight pairing rules. The Postgres volume persists changes across restarts. To stop the service, use `docker compose stop`.

**Mac/Linux alternative** with Python 3.11+ and internet access for the initial dependency install:

    sh start-demo.sh

This uses the included compiled Vue app and creates a local SQLite database. No Node installation is needed for this route. Use PostgreSQL for multi-device service. Both startup options bind to loopback by default. Avoid running them simultaneously on port 8080.

## Five-minute walkthrough
1. Enter the manager demo. In **Service floor**, select **Table 07**, then **Open demo display**. Allow the new tab to open. The quiet screen is an actual paired device. On a tablet use a one-time code from **Table displays** instead.
2. In the service panel select **Open session**, then press **+** beside **Grilled Steak**. Select **Send recommendation signal**. The display shows Garlic Mushrooms (£4.50) and Fresh Lemonade (£3.25) with explanations. Only this table receives them. Initial demo control allocation is 0% so the walkthrough is repeatable.
3. On the display choose **Not now**. On the staff screen find **Session pairings** and mark **requested**, then **fulfilled**, for the item the guest requested verbally. Both are distinct manual records. Selection traces are visible to a manager. A background tab may not record an impression until brought to the foreground.
4. **Close session & clear display**. Open the next session to see a clean guest screen. Open **Pilot insights**, refresh and inspect the event journal or export its CSV.
5. Try a new session with House Burger plus Seasoned Fries already ordered. Fresh Lemonade remains eligible. In Menu library make Lemonade unavailable before the next signal to test the quiet state. Re-enable it afterwards. For a control demonstration, set control allocation to 100% and open a fresh session.
6. To reopen an existing paired display in the same browser profile, visit **/#/display**. To pair a new browser or deliberately reassign a device, issue a fresh code and visit **/#/display?setup=1**. Use a separate browser profile per simulated device.

## Included
- Vue 3, TypeScript, Pinia, Vue Router and Vite sources plus built client. Django, Django REST Framework, versioned migrations, PostgreSQL Compose configuration and a local SQLite mode.
- Authenticated and venue-scoped owner, manager and staff access. One-time expiring pairing codes, hashed device credentials, table-specific updates, heartbeat, session reset and CSV export.
- Manager-set pricing, approval expiry, costs, availability, image URLs, dietary tags and allergen notes. Item/category rules, priorities, time windows, exclusions, frequency caps, dietary preferences and manual dessert stage.
- Separate, disabled-by-default approved surplus specials module. Instructions and guardrails are in docs/operations.md.
- Reproducible backend, frontend and browser checks. See docs/verification.md.
- Runbooks for architecture, API, devices, deployment and pilot measurement under docs/.

Use real approved venue data before service. Demo prices, photos and ingredient notes are illustrative. Catalog approval expires after 30 days in the seed. See **Menu library → Edit** to review and renew it.
