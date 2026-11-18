# Architecture and data model
The Django process serves both the compiled Vue application and same-origin REST endpoints. PostgreSQL stores pilot records. The lightweight local launcher uses SQLite. No paid inference, Redis or external services are required. Monetary values are integer pence. A single account has one venue membership in this pilot.

~~~mermaid
flowchart TD
  Staff[Staff phone] -->|Meal signal| API[Django API]
  Manager[Manager console] -->|Catalog and rules| API
  API --> Engine[Eligibility and scoring]
  Engine --> DB[(PostgreSQL)]
  DB --> API
  API -->|Current state and refresh hints| Tablet[Paired display]
  Tablet -->|Impression or dismissal| API
~~~

~~~mermaid
erDiagram
  VENUE ||--o{ MEMBERSHIP : authorizes
  VENUE ||--o{ TABLE : contains
  VENUE ||--o{ ITEM : owns
  TABLE ||--o| DEVICE : pairs
  TABLE ||--o{ VISIT : seats
  VISIT ||--o{ SIGNAL : receives
  SIGNAL ||--|{ LINE : contains
  ITEM ||--o{ LINE : identifies
  VENUE ||--o{ RULE : defines
  RULE ||--o| PROMOTION : restricts
  RULE ||--o{ SUGGESTION : selects
  VISIT ||--o{ SUGGESTION : receives
  SUGGESTION ||--o{ OUTCOME : records
  TABLE ||--o{ EVENT : logs
~~~

A venue and table lock guards session opening. A partial unique index permits one open visit. Incoming signal processing locks its visit, validates rows and commits the signal, selection and journal together. Retry the same request using its original key. Each signal adds known ordered items to the visit. New signals supersede prior ready cards. New session IDs preserve the party boundary.

RuleScorer ranks exact triggers above category triggers, then manager priority, estimated unit contribution and stable rule ID. Dietary tags, exclusions, approved price/availability, time windows, stage, earlier dismissals and capped counts constrain output. Caps count issued cards conservatively, even if the device went offline before rendering. Each selection records rule and catalog versions plus score components. Catalog or rule edits invalidate outstanding cards. Managers can inspect the trace from the table panel.

Display clients use bearer-authenticated server-sent refresh hints, short fetch-current-state polling and a local expiry timer. The streaming endpoint sends hints only and periodically reconnects. A network error clears visible content. The browser offline event clears immediately. Silent failures are bounded by polling interval and a five-second fetch timeout. The server records an impression only after visible-page acknowledgement. Staff and manager previews of the state do not count. Heartbeat status is computed when an operator loads the floor. The floor records an offline transition when it observes a paired device whose last heartbeat is over 20 seconds old.

Experiment assignment uses a hash of a fresh anonymous visit UUID and stores the result at opening. Eligibility is measured in both cohorts before control suppression. The dashboard distinguishes card impressions, reported requests and staff-confirmed additions. It withholds verified sales and causal contribution until trustworthy comparable sales data exist.
