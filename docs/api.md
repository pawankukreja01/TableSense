# API
All routes below begin with /api. Staff and managers sign in using a Django session cookie. GET /bootstrap supplies a CSRF cookie. For session writes include X-CSRFToken with the cookie value. Pairing redeems a short-lived one-time code. Guest endpoints require Authorization: Bearer <device token>. Device requests send no staff cookies. Prices and costs are nonnegative integer minor units. Times are ISO 8601; the service accepts UTC timestamps for special offers. Venue-local time applies to pairing-rule service windows.

|Method|Path|Actor and purpose|
|---|---|---|
|GET|/health, /bootstrap|Database readiness, then auth/demo state|
|POST|/login, /logout|Login accepts username and password|
|GET|/floor|Staff/manager table status, current cards, menu and session history|
|GET, POST|/items, /rules|Manager lists or creates venue catalog entries|
|PATCH|/items/{id}, /rules/{id}|Update fields, including availability, approval cutoff, rule priority and exclusions|
|POST|/tables/{id}/open|Create anonymous visit with fixed experiment assignment|
|POST|/visits/{id}/signals|Validate and deduplicate the staff or simulated POS signal|
|POST|/visits/{id}/close|Close visit and invalidate its cards|
|POST|/suggestions/{id}/outcome|Staff records requested, fulfilled, not_fulfilled or unknown|
|POST|/tables/{id}/problem|Staff submits detail with device issue or anonymous feedback|
|POST|/tables/{id}/device|Manager issues a five-minute code; action=unpair revokes credentials|
|POST|/pair|Redeem code; returns token once and rotates earlier token|
|GET, POST|/display|Guest-safe state and heartbeat; POST supports optional battery percentage, action=shown or dismiss, and ids array|
|GET|/display/updates|Bearer-authenticated SSE refresh hints|
|GET, POST|/settings|Manager controls, theme, venue name, HTTPS logo|
|GET|/report, /events.csv|Venue cohort totals, recent events, manual capture times and full journal export|
|GET, POST|/promotions|Flagged manager module. Create an approved special, list specials, or withdraw by ID|

Example request to /visits/42/signals (replace example IDs with local ones):

~~~json
{"key":"service-42-001","origin":"staff","stage":"main","preferences":["vegetarian"],"capture_seconds":8,"lines":[{"item":3,"quantity":2}]}
~~~

The authenticated membership and visit resolve venue and table. The server stamps receipt time. StaffSelectorAdapter and MockPOSAdapter share validation and evaluation. Selecting mock_pos in demo mode simulates receipt through this internal API. A future external adapter must authenticate its provider, validate signatures, map external table/item IDs, preserve provider timestamps separately and translate adjustments, voids and stable event keys. This version exposes no public vendor webhook or live POS connector.

A duplicate key for a visit returns the original signal ID and duplicate=true. Use a fresh key for a genuinely new signal. Validation errors return 400, missing/out-of-scope objects 404 and unauthorized actions 401/403. Pairing and sign-in attempts are throttled. Code renewal for an already paired table keeps the original device live until the new code is redeemed.
