<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  Plus,
  Search,
  X,
  Pencil,
  Tablet,
  Download,
  GitBranch,
  Image as Photo,
} from "lucide-vue-next";
import { api, useDesk, money } from "./store";
const props = defineProps<{ page: string }>(),
  d = useDesk(),
  query = ref(""),
  group = ref("All"),
  rules = ref<any[]>([]),
  form = ref<any>(null),
  report = ref<any>(null),
  settings = ref<any>(null),
  error = ref(""),
  msg = ref(""),
  codes = ref<Record<number, string>>({}),
  busy = ref(false);
const names: Record<string, string> = {
  menu: "Menu library",
  pairings: "Pairing rules",
  devices: "Table displays",
  insights: "Pilot insights",
  settings: "Service settings",
};
const descriptions: Record<string, string> = {
  menu: "Manage the dishes, prices and availability used in table recommendations.",
  pairings: "Choose which additions belong alongside each meal.",
  devices: "Pair each guest screen with its dining table.",
  insights:
    "Follow anonymous sessions from eligibility to staff-reported outcomes.",
  settings:
    "Set recommendation limits and the share of new sessions assigned to control.",
};
const categories = ["Main", "Side", "Drink", "Dessert"],
  itemName = (id: number) => d.menu.find((x) => x.id === id)?.name || "—";
async function load() {
  if (props.page === "pairings") rules.value = await api("rules");
  if (props.page === "insights") report.value = await api("report");
  if (props.page === "settings") settings.value = await api("settings");
}
async function run(fn: () => Promise<unknown>, note = "") {
  if (busy.value) return;
  busy.value = true;
  msg.value = error.value = "";
  try {
    await fn();
    await d.load();
    await load();
    msg.value = note;
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
onMounted(() => run(async () => {}));
function edit(row?: any) {
  error.value = msg.value = "";
  if (props.page === "menu") {
    const f = row
      ? { ...row }
      : {
          name: "",
          category: "Side",
          price: 0,
          cost: 0,
          description: "",
          image: "",
          tags: "",
          allergens: "",
          active: true,
          available: true,
          approved_until: new Date(Date.now() + 7 * 86400000).toISOString(),
        };
    f.pounds = f.price / 100;
    f.costPounds = f.cost / 100;
    f.date = new Date(
      new Date(f.approved_until).getTime() -
        new Date(f.approved_until).getTimezoneOffset() * 60000,
    )
      .toISOString()
      .slice(0, 16);
    form.value = f;
  } else
    form.value = row
      ? { ...row, exclusions: [...row.exclusions] }
      : {
          trigger: null,
          category: "Main",
          candidate: d.menu.find((i) => i.category === "Side")?.id,
          reason: "",
          stage: "main",
          priority: 10,
          max_shows: 1,
          exclusions: [],
          active: true,
          start: null,
          end: null,
        };
}
async function save() {
  await run(async () => {
    let f = { ...form.value };
    const kind = props.page === "menu" ? "items" : "rules";
    if (kind === "items") {
      f.price = Math.round(f.pounds * 100);
      f.cost = Math.round(f.costPounds * 100);
      f.approved_until = new Date(f.date).toISOString();
    } else {
      if (f.trigger) f.category = "";
      f.start = f.start || null;
      f.end = f.end || null;
    }
    await api(kind + (f.id ? "/" + f.id : ""), f, f.id ? "PATCH" : "POST");
    form.value = null;
  }, "Changes saved.");
}
</script>
<template>
  <div class="heading">
    <div>
      <span class="eyebrow"><i /> OWNER CONSOLE</span>
      <h1>{{ names[page] }}</h1>
      <p>{{ descriptions[page] }}</p>
    </div>
    <button
      v-if="['menu', 'pairings'].includes(page)"
      class="primary"
      @click="edit()"
    >
      <Plus />{{ page === "menu" ? "New item" : "New rule" }}
    </button>
  </div>
  <p v-if="msg" role="status" class="notice">{{ msg }}</p>
  <p v-if="error && !form" role="alert" class="error">{{ error }}</p>
  <template v-if="page === 'menu'"
    ><div class="sectionHead">
      <div class="tabs">
        <button
          v-for="c in ['All', ...categories]"
          :class="{ on: group === c }"
          @click="group = c"
        >
          {{ c }}
        </button>
      </div>
      <input
        class="search"
        v-model="query"
        aria-label="Search menu"
        placeholder="Search menu…"
      />
    </div>
    <div class="menuGrid">
      <article
        v-for="i in d.menu.filter(
          (x) =>
            (group === 'All' || x.category === group) &&
            x.name.toLowerCase().includes(query.toLowerCase()),
        )"
      >
        <img v-if="i.image" :src="i.image" :alt="i.name" />
        <div v-else class="placeholder"><Photo /></div>
        <div class="menuInfo">
          <span class="eyebrow">{{ i.category }}</span>
          <h3>{{ i.name }}</h3>
          <div class="sectionHead">
            <b>{{ money(i.price) }}</b
            ><button
              class="icon"
              :aria-label="'Edit ' + i.name"
              @click="edit(i)"
            >
              <Pencil :size="16" />
            </button>
          </div>
          <button
            class="pill"
            :class="{ green: i.available }"
            :disabled="busy"
            @click="
              run(
                () =>
                  api('items/' + i.id, { available: !i.available }, 'PATCH'),
                'Availability updated.',
              )
            "
          >
            <i />{{ i.available ? "Available" : "Unavailable" }}
          </button>
        </div>
      </article>
    </div></template
  >
  <div v-if="page === 'pairings'" class="panel">
    <article v-for="r in rules" class="line">
      <div>
        <span class="eyebrow"
          >{{ r.stage }} · Priority {{ r.priority }} ·
          {{ r.active ? "Active" : "Paused" }}</span
        >
        <h3>
          {{ r.trigger ? itemName(r.trigger) : r.category }} →
          {{ itemName(r.candidate) }}
        </h3>
        <p>{{ r.reason }}</p>
      </div>
      <button class="icon" :aria-label="'Edit rule ' + r.id" @click="edit(r)">
        <Pencil />
      </button>
    </article>
  </div>
  <div v-if="page === 'devices'" class="deviceGrid">
    <article class="panel" v-for="t in d.tables">
      <div class="sectionHead">
        <Tablet /><span class="pill" :class="{ green: t.online }"
          ><i />{{
            t.online ? "Online" : t.paired ? "Offline" : "Unpaired"
          }}</span
        >
      </div>
      <h3>{{ t.label }}</h3>
      <small
        >Last seen ·
        {{
          t.last_seen
            ? new Date(t.last_seen).toLocaleString()
            : "Awaiting device"
        }}<br />Battery ·
        {{ t.battery === null ? "Unavailable" : t.battery + "%" }} ·
        {{ t.version || "No version reported" }}</small
      >
      <div class="actions">
        <button
          @click="
            run(async () => {
              codes[t.id] = (await api('tables/' + t.id + '/device', {})).code;
            })
          "
        >
          Create pairing code</button
        ><button
          v-if="t.paired || codes[t.id]"
          @click="
            run(async () => {
              await api('tables/' + t.id + '/device', { action: 'unpair' });
              delete codes[t.id];
            }, 'Device removed.')
          "
        >
          Unpair
        </button>
      </div>
      <div v-if="codes[t.id]" class="notice">
        <strong>{{ codes[t.id] }}</strong> · valid 5 min
      </div>
    </article>
    <a href="#/display?setup=1" target="_blank" class="secondary"
      >Open pairing screen ↗</a
    >
  </div>
  <template v-if="page === 'insights' && report"
    ><div class="sectionHead">
      <h2>Experiment comparison</h2>
      <button class="secondary" @click="run(async () => {})">Refresh</button>
    </div>
    <div class="panel scroll">
      <table>
        <thead>
          <tr>
            <th>Cohort</th>
            <th>Sessions</th>
            <th>Eligible</th>
            <th>Impressions</th>
            <th>Dismissed</th>
            <th>Requested</th>
            <th>Fulfilled¹</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in report.groups">
            <td
              v-for="k in [
                'group',
                'sessions',
                'eligible',
                'recommendation_shown',
                'recommendation_dismissed',
                'staff_marked_requested',
                'staff_marked_fulfilled',
              ]"
            >
              {{ g[k] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="hint">
      ¹ Staff-confirmed additions are manually reported. POS-verified purchases
      and incremental contribution are unavailable until comparable sales and
      costs are linked for both cohorts.
    </p>
    <div class="panel">
      <strong>Manual capture time</strong>
      <p>
        {{
          report.capture_seconds.length
            ? (
                report.capture_seconds.reduce(
                  (a: number, b: number) => a + b,
                  0,
                ) / report.capture_seconds.length
              ).toFixed(1) + " seconds on average"
            : "No manual signals recorded"
        }}
        · latest 100 signals
      </p>
    </div>
    <div class="sectionHead">
      <h2>Event journal</h2>
      <a class="secondary" href="/api/events.csv" download
        ><Download :size="16" />Export CSV</a
      >
    </div>
    <div class="panel">
      <p v-if="!report.events.length">
        Events appear here when service begins.
      </p>
      <div v-for="e in report.events" class="line">
        <div>
          <strong>{{ e.kind.replaceAll("_", " ") }}</strong
          ><small
            >{{ e.table__label }} · {{ e.origin }} ·
            {{ e.detail || e.verification }}</small
          >
        </div>
        <small>{{ new Date(e.created).toLocaleTimeString() }}</small>
      </div>
    </div></template
  >
  <form
    v-if="page === 'settings' && settings"
    class="panel settings"
    @submit.prevent="
      run(() => api('settings', settings), 'Service settings saved.')
    "
  >
    <h2>Service controls</h2>
    <label
      >Venue name<input
        required
        maxlength="80"
        v-model="settings.name" /></label
    ><label
      >Guest display accent<input
        type="color"
        v-model="settings.accent" /></label
    ><label
      >Venue logo URL<input
        type="url"
        v-model="settings.logo"
        placeholder="https://" /></label
    ><label
      v-for="(label, k) in {
        control_percent: 'Control allocation (%)',
        seconds: 'Display duration (seconds)',
        session_cap: 'Maximum cards per session',
        stage_cap: 'Maximum cards per stage',
      }"
      >{{ label }}<input required type="number" v-model.number="settings[k]"
    /></label>
    <p class="hint">
      Experiment allocation applies when a new session opens. Existing sessions
      keep their assignment.
    </p>
    <button class="primary">Save settings</button>
  </form>
  <div v-if="form" class="overlay" @keydown.esc="form = null">
    <form class="drawer" @submit.prevent="save">
      <div class="sectionHead">
        <h2>
          {{ form.id ? "Edit" : "New" }}
          {{ page === "menu" ? "menu item" : "pairing rule" }}
        </h2>
        <button
          type="button"
          class="icon"
          @click="form = null"
          aria-label="Close editor"
        >
          <X />
        </button>
      </div>
      <template v-if="page === 'menu'"
        ><label
          >Item name<input v-model="form.name" maxlength="80" required /></label
        ><label
          >Category<select v-model="form.category">
            <option v-for="c in categories">{{ c }}</option>
          </select></label
        >
        <div class="formgrid">
          <label
            >Price (£)<input
              v-model.number="form.pounds"
              type="number"
              min="0.01"
              step=".01"
              required /></label
          ><label
            >Variable cost (£)<input
              v-model.number="form.costPounds"
              type="number"
              min="0"
              step=".01"
              required
          /></label>
        </div>
        <label
          v-for="(v, k) in {
            description: 'Description',
            image: 'Image URL or bundled image path',
            tags: 'Dietary tags (comma separated)',
            allergens: 'Restaurant allergen notes',
          }"
          >{{ v }}<input v-model="form[k]" /></label
        ><label
          >Availability and price approved until<input
            type="datetime-local"
            v-model="form.date"
            required /></label
        ><label class="check"
          ><input type="checkbox" v-model="form.available" />Available</label
        ></template
      >
      <template v-else
        ><label
          >Trigger item<select v-model="form.trigger">
            <option :value="null">Use category instead</option>
            <option v-for="i in d.menu" :value="i.id">{{ i.name }}</option>
          </select></label
        ><label v-if="!form.trigger"
          >Trigger category<select v-model="form.category">
            <option v-for="c in categories">{{ c }}</option>
          </select></label
        ><label
          >Recommended item<select v-model="form.candidate">
            <option v-for="i in d.menu" :value="i.id">{{ i.name }}</option>
          </select></label
        ><label
          >Pairing reason<input
            v-model="form.reason"
            maxlength="160"
            required /></label
        ><label
          >Dining stage<select v-model="form.stage">
            <option>main</option>
            <option>dessert</option>
          </select></label
        >
        <div class="formgrid">
          <label
            >Priority<input
              type="number"
              min="0"
              v-model.number="form.priority"
              required /></label
          ><label
            >Maximum shows<input
              type="number"
              min="1"
              v-model.number="form.max_shows"
              required /></label
          ><label>Window start<input type="time" v-model="form.start" /></label
          ><label>Window end<input type="time" v-model="form.end" /></label>
        </div>
        <label
          >Suppress when ordered<select multiple v-model="form.exclusions">
            <option v-for="i in d.menu" :value="i.id">{{ i.name }}</option>
          </select></label
        ></template
      ><label class="check"
        ><input type="checkbox" v-model="form.active" />Active</label
      ><button class="primary" :disabled="busy">Save changes</button>
      <p class="error" v-if="error">{{ error }}</p>
    </form>
  </div>
</template>
