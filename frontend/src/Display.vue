<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Sprout, Utensils, Tablet } from "lucide-vue-next";
import { api, money, type Card } from "./store";
const route = useRoute(),
  router = useRouter(),
  token = ref(localStorage.getItem("tablesense-device") || ""),
  code = ref(""),
  err = ref(""),
  off = ref(false),
  state = ref<any>(null),
  cards = ref<Card[]>([]),
  motion = ref(localStorage.getItem("tablesense-motion") === "1");
let battery: { level: number } | undefined;
let hints: AbortController | undefined, hintTimer: number;
async function listen() {
  if (!alive || !token.value) return;
  hints = new AbortController();
  try {
    const r = await fetch("/api/display/updates", {
      credentials: "omit",
      headers: { Authorization: "Bearer " + token.value },
      signal: hints.signal,
    });
    if (!r.ok || !r.body) throw Error();
    const stream = r.body.getReader(),
      decoder = new TextDecoder();
    let pending = "";
    while (alive) {
      const part = await stream.read();
      if (part.done) break;
      pending += decoder.decode(part.value, { stream: true });
      let split = pending.indexOf("\n\n");
      while (split >= 0) {
        const block = pending.slice(0, split);
        pending = pending.slice(split + 2);
        if (block.startsWith("data:")) await pull();
        split = pending.indexOf("\n\n");
      }
    }
  } catch {
    /* Polling continues if streaming is unavailable. */
  } finally {
    if (alive) hintTimer = window.setTimeout(listen, 2500);
  }
}
let timer: number,
  expiry: number,
  gen = 0,
  alive = true;
function clear() {
  cards.value = [];
  state.value = null;
  clearTimeout(expiry);
}
function offline() {
  gen++;
  clear();
  off.value = true;
}
async function pull() {
  if (!alive || !token.value) return;
  const version = ++gen;
  try {
    const s = await api(
      "display",
      battery ? { battery: Math.round(battery.level * 100) } : undefined,
      undefined,
      token.value,
    );
    if (version !== gen || !alive) return;
    state.value = s;
    off.value = false;
    cards.value = s.cards.filter(
      (r: Card) => Date.parse(r.expires) > Date.now(),
    );
    clearTimeout(expiry);
    if (cards.value.length) {
      expiry = window.setTimeout(
        () => {
          cards.value = [];
        },
        Math.max(
          0,
          Math.min(...cards.value.map((r) => Date.parse(r.expires))) -
            Date.now(),
        ),
      );
      await nextTick();
      if (!document.hidden && version === gen) {
        await api(
          "display",
          { action: "shown", ids: cards.value.map((r) => r.id) },
          undefined,
          token.value,
        );
      }
    }
  } catch {
    if (version === gen) offline();
  }
}
async function pair() {
  err.value = "";
  try {
    const r = await api("pair", { code: code.value });
    token.value = r.token;
    localStorage.setItem("tablesense-device", r.token);
    await router.replace("/display");
    await pull();
  } catch {
    err.value = "Pairing failed. Ask the manager for a fresh code.";
  }
}
async function dismiss() {
  const ids = cards.value.map((r) => r.id);
  gen++;
  cards.value = [];
  try {
    await api("display", { action: "dismiss", ids }, undefined, token.value);
    await pull();
  } catch {
    offline();
  }
}
async function tick() {
  await pull();
  if (alive) timer = window.setTimeout(tick, 1800);
}
function saveMotion() {
  localStorage.setItem("tablesense-motion", motion.value ? "1" : "0");
}
function visibility() {
  if (document.hidden) {
    gen++;
    clear();
  } else pull();
}
onMounted(async () => {
  if (route.query.setup) {
    token.value = "";
    localStorage.removeItem("tablesense-device");
  }
  const nav = navigator as Navigator & {
    getBattery?: () => Promise<{ level: number }>;
  };
  nav
    .getBattery?.()
    .then((b) => (battery = b))
    .catch(() => {});
  if (route.query.code) {
    code.value = String(route.query.code);
    await pair();
  }
  window.addEventListener("offline", offline);
  window.addEventListener("online", pull);
  document.addEventListener("visibilitychange", visibility);
  listen();
  await tick();
});
onBeforeUnmount(() => {
  alive = false;
  hints?.abort();
  clearTimeout(hintTimer);
  gen++;
  clearTimeout(timer);
  clearTimeout(expiry);
  window.removeEventListener("offline", offline);
  window.removeEventListener("online", pull);
  document.removeEventListener("visibilitychange", visibility);
});
</script>
<template>
  <main v-if="!token" class="pairPage panel">
    <Tablet />
    <h1>Pair this display</h1>
    <p>Enter the one-time code from the manager’s Table displays screen.</p>
    <form @submit.prevent="pair">
      <label
        >Pairing code<input
          required
          v-model="code"
          maxlength="8"
          autocomplete="off"
          autofocus /></label
      ><button class="primary">Pair display</button>
    </form>
    <p class="error" v-if="err">{{ err }}</p>
  </main>
  <main
    v-else
    class="guest"
    :class="{ still: motion }"
    :style="{ '--accent': state?.accent || '#315b43' }"
  >
    <header>
      <span class="guestBrand"
        ><img v-if="state?.logo" :src="state.logo" alt="" /><Sprout v-else />{{
          state?.venue || "TableSense"
        }}</span
      ><span>{{ state?.table }}</span>
    </header>
    <div v-if="cards.length" class="guestInner">
      <span class="eyebrow">A PAIRING FROM OUR KITCHEN</span>
      <h1>Complete your meal</h1>
      <p>With your {{ state.with.toLowerCase() }}</p>
      <div class="guestCards">
        <article v-for="r in cards">
          <img v-if="r.image" :src="r.image" :alt="r.name" />
          <div>
            <span class="eyebrow">{{
              r.special ? "Today’s special" : r.category
            }}</span>
            <h2>{{ r.name }}</h2>
            <strong>{{ money(r.price, state.currency) }}</strong>
            <p>{{ r.reason }}</p>
          </div>
        </article>
      </div>
      <div class="guestFooter">
        <strong>Please ask your waiter to add an item.</strong
        ><button class="secondary" @click="dismiss">Not now</button>
      </div>
    </div>
    <div v-else class="quiet">
      <Sprout /><span class="eyebrow">{{
        off ? "DISPLAY OFFLINE" : "WELCOME TO THE TABLE"
      }}</span>
      <h1>{{ off ? "Enjoy your meal." : state?.venue || "Welcome" }}</h1>
      <p>
        {{
          off ? "Your waiter is here to help." : "Make yourself comfortable."
        }}
      </p>
    </div>
    <footer>
      <span
        >{{
          state?.demo ? "Demo menu · illustrative prices and photography" : ""
        }}{{
          state?.battery != null && state.battery < 15 ? " · Low battery" : ""
        }}</span
      ><button
        class="plain"
        @click="
          motion = !motion;
          saveMotion();
        "
      >
        {{ motion ? "Reduced motion on" : "Reduce motion" }}
      </button>
    </footer>
  </main>
</template>
