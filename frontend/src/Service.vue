<script setup lang="ts">
import { ref, computed } from "vue";
import {
  ArrowRight,
  ArrowUpRight,
  LayoutGrid,
  Monitor,
  Utensils,
  Radio,
  X,
  Plus,
  Minus,
  Send,
  Check,
  Tablet,
} from "lucide-vue-next";
import { api, useDesk, money, type Table } from "./store";
const d = useDesk(),
  selected = ref(0),
  filter = ref("All tables"),
  category = ref("Main"),
  qty = ref<Record<number, number>>({}),
  stage = ref("main"),
  pref = ref(""),
  origin = ref("staff"),
  error = ref(""),
  msg = ref(""),
  busy = ref(false),
  issue = ref("");
const t = computed(() => d.tables.find((x) => x.id === selected.value)),
  open = computed(() => d.tables.filter((x) => x.visit).length),
  showing = computed(() => d.tables.filter((x) => x.cards.length).length);
const tables = computed(() =>
  d.tables.filter(
    (x) =>
      filter.value === "All tables" ||
      (filter.value === "In service" ? !!x.visit : !x.visit),
  ),
);
let started = 0,
  key = "";
function reset() {
  qty.value = {};
  category.value = "Main";
  stage.value = "main";
  pref.value = "";
  origin.value = "staff";
  key = crypto.randomUUID();
  started = Date.now();
}
function pick(table: Table) {
  selected.value = table.id;
  error.value = msg.value = issue.value = "";
  reset();
}
async function run(fn: () => Promise<unknown>, note: string) {
  if (busy.value) return;
  busy.value = true;
  error.value = msg.value = "";
  try {
    await fn();
    await d.load();
    msg.value = note;
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
async function send() {
  if (!t.value) return;
  const visit = t.value.visit;
  await run(async () => {
    await api("visits/" + visit + "/signals", {
      key,
      stage: stage.value,
      preferences: pref.value ? [pref.value] : [],
      origin: origin.value,
      lines: Object.entries(qty.value)
        .filter(([, q]) => q > 0)
        .map(([id, quantity]) => ({ item: Number(id), quantity })),
      capture_seconds: Math.min(
        86400,
        Math.round((Date.now() - started) / 1000),
      ),
    });
    reset();
  }, "Signal received. The display will refresh automatically.");
}
async function preview() {
  if (!t.value) return;
  const tab = window.open("about:blank", "_blank");
  await run(async () => {
    if (!tab) throw Error("Allow pop-ups for the display.");
    try {
      const { code } = await api("tables/" + selected.value + "/device", {});
      tab.location.href = location.pathname + "#/display?code=" + code;
    } catch (e) {
      tab.close();
      throw e;
    }
  }, "Demo display opened in a separate tab.");
}
</script>
<template>
  <div class="heading">
    <div>
      <span class="eyebrow"><i /> SERVICE WORKSPACE</span>
      <h1>Service floor</h1>
      <p>Manage table sessions and send meal pairings to your displays.</p>
    </div>
  </div>
  <div v-if="d.demo && d.venue === 'Demo Bistro'" class="serviceHero">
    <div>
      <span class="eyebrow">HOUSE PAIRING</span>
      <h2>Grilled steak <em>&amp;</em><br />garlic mushrooms</h2>
      <p>From the {{ d.venue }} pilot menu</p>
    </div>
  </div>
  <div class="stats">
    <div
      v-for="s in [
        { name: 'Dining tables', num: d.tables.length, icon: LayoutGrid },
        { name: 'In service', num: open, icon: Utensils },
        { name: 'Tables with pairings', num: showing, icon: Radio },
        {
          name: 'Displays online',
          num: d.tables.filter((x) => x.online).length,
          icon: Monitor,
        },
      ]"
      :key="s.name"
    >
      <component :is="s.icon" />
      <section>
        <small>{{ s.name }}</small
        ><strong>{{ s.num }}</strong>
      </section>
    </div>
  </div>
  <div class="sectionHead">
    <h2>Dining room</h2>
    <select aria-label="Filter tables" v-model="filter">
      <option>All tables</option>
      <option>In service</option>
      <option>Available</option>
    </select>
  </div>
  <div class="tiles">
    <button v-for="x in tables" :key="x.id" @click="pick(x)">
      <span class="tileTop"><LayoutGrid /><ArrowUpRight :size="16" /></span>
      <h3>{{ x.label }}</h3>
      <span class="pill" :class="{ green: x.visit }"
        ><i />{{
          x.cards.length
            ? "Pairing ready"
            : x.visit
              ? "In service"
              : "Available"
        }}</span
      >
    </button>
  </div>
  <p v-if="!tables.length" class="empty">No tables match this filter.</p>
  <div
    v-if="t"
    class="overlay"
    @click.self="selected = 0"
    @keydown.esc="selected = 0"
  >
    <section
      class="drawer"
      role="dialog"
      aria-modal="true"
      :aria-label="t.label"
    >
      <div class="sectionHead">
        <div>
          <span class="eyebrow">TABLE SESSION</span>
          <h2>{{ t.label }}</h2>
        </div>
        <button class="icon" aria-label="Close panel" @click="selected = 0">
          <X />
        </button>
      </div>
      <div class="strip">
        <Tablet :size="18" />{{
          t.online
            ? "Display connected"
            : t.paired
              ? "Display offline"
              : "Display unpaired"
        }}<button
          v-if="d.demo && d.role !== 'staff' && !t.paired"
          class="textBtn"
          @click="preview"
        >
          Open demo display ↗
        </button>
      </div>
      <p v-if="!t.visit">Open an anonymous session when guests are seated.</p>
      <button
        v-if="!t.visit"
        class="primary"
        :disabled="busy"
        @click="
          run(() => api('tables/' + t!.id + '/open', {}), 'Session opened.')
        "
      >
        Open session <Plus />
      </button>
      <template v-else
        ><div class="sectionHead">
          <h3>Meal signal</h3>
          <span class="pill">{{
            t.control ? "Control group" : "Treatment group"
          }}</span>
        </div>
        <p class="hint">
          Manual entry is a temporary pilot workaround. Record the order in your
          usual POS first.
        </p>
        <div class="formgrid">
          <label
            >Dining stage<select v-model="stage">
              <option value="main">Main course</option>
              <option value="dessert">Dessert</option>
            </select></label
          ><label
            >Dietary preference<select v-model="pref">
              <option value="">Unspecified</option>
              <option>vegetarian</option>
              <option>vegan</option>
            </select></label
          >
        </div>
        <div class="tabs">
          <button
            v-for="c in ['Main', 'Side', 'Drink', 'Dessert']"
            :class="{ on: category === c }"
            @click="category = c"
          >
            {{ c }}
          </button>
        </div>
        <div
          v-for="i in d.menu.filter((i) => i.category === category)"
          class="line"
        >
          <span
            >{{ i.name }}<small>{{ money(i.price) }}</small></span
          >
          <div class="step">
            <button
              :aria-label="'Remove ' + i.name"
              :disabled="!qty[i.id]"
              @click="qty[i.id]--"
            >
              <Minus /></button
            >{{ qty[i.id] || 0
            }}<button
              :aria-label="'Select ' + i.name"
              @click="qty[i.id] = Math.min(99, (qty[i.id] || 0) + 1)"
            >
              <Plus />
            </button>
          </div>
        </div>
        <label v-if="d.demo"
          >Signal source<select v-model="origin">
            <option value="staff">Staff selector</option>
            <option value="mock_pos">Simulated POS adapter</option>
          </select></label
        ><button
          class="primary"
          :disabled="busy || !Object.values(qty).some((x) => x > 0)"
          @click="send"
        >
          Send recommendation signal <Send />
        </button>
        <div v-if="t.history.length">
          <h3>Session pairings</h3>
          <article v-for="r in t.history" class="recLine">
            <strong>{{ r.name }} · {{ money(r.price) }}</strong
            ><small
              >{{ r.status }} ·
              {{
                r.seen ? "Impression recorded" : "Awaiting impression"
              }}</small
            >
            <details v-if="r.trace">
              <summary>Selection trace</summary>
              <pre>{{ JSON.stringify(r.trace, null, 2) }}</pre>
            </details>
            <div v-if="r.seen" class="actions">
              <button
                v-for="s in [
                  'requested',
                  'fulfilled',
                  'not_fulfilled',
                  'unknown',
                ]"
                :disabled="busy || r.outcomes?.includes(s)"
                @click="
                  run(
                    () =>
                      api('suggestions/' + r.id + '/outcome', { status: s }),
                    'Manual outcome recorded.',
                  )
                "
              >
                {{ r.outcomes?.includes(s) ? "✓ " : ""
                }}{{ s.replace("_", " ") }}
              </button>
            </div>
          </article>
        </div>
        <button
          class="secondary"
          :disabled="busy"
          @click="
            run(
              () => api('visits/' + t!.visit + '/close', {}),
              'Session closed. Display cleared.',
            )
          "
        >
          Close session &amp; clear display
        </button></template
      >
      <details>
        <summary>Report a device issue</summary>
        <label
          >Issue or service feedback<input
            v-model="issue"
            maxlength="200"
            placeholder="Describe the issue" /></label
        ><button
          :disabled="busy || !issue.trim()"
          class="secondary"
          @click="
            run(
              () => api('tables/' + t!.id + '/problem', { detail: issue }),
              'Report saved.',
            )
          "
        >
          Save report
        </button>
      </details>
      <p v-if="msg" role="status" class="notice">
        <Check :size="16" />{{ msg }}
      </p>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
    </section>
  </div>
</template>
