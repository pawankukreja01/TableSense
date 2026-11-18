<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Sprout,
  LayoutGrid,
  BookOpen,
  GitBranch,
  Tablet,
  ChartNoAxesColumn,
  SlidersHorizontal,
  LogOut,
  ArrowUpRight,
  ArrowRight,
  Radio,
  Utensils,
  PanelLeftClose,
} from "lucide-vue-next";
import { api, useDesk } from "./store";
import Specials from "./Specials.vue";
import Service from "./Service.vue";
import Manager from "./Manager.vue";
const d = useDesk(),
  route = useRoute(),
  router = useRouter();
const page = computed(() => String(route.params.page || "service"));
const sections = [
  { id: "service", name: "Service floor", icon: LayoutGrid },
  { id: "menu", name: "Menu library", icon: BookOpen },
  { id: "pairings", name: "Pairing rules", icon: GitBranch },
  { id: "devices", name: "Table displays", icon: Tablet },
  { id: "insights", name: "Pilot insights", icon: ChartNoAxesColumn },
  { id: "specials", name: "Approved specials", icon: Sprout },
  { id: "settings", name: "Service settings", icon: SlidersHorizontal },
];
const user = ref(""),
  pass = ref(""),
  err = ref(""),
  ready = ref(false),
  busy = ref(false),
  mobile = ref(false),
  manual = ref(false);
let timer: number;
async function refresh() {
  try {
    await d.load();
    err.value = "";
  } catch (e) {
    err.value = String(e);
  }
}
async function enter(role = "") {
  busy.value = true;
  try {
    await api("login", {
      username: role ? "demo-" + role : user.value,
      password: role ? "bistro-demo" : pass.value,
    });
    await refresh();
    router.replace("/service");
  } catch (e) {
    err.value = String(e);
  } finally {
    busy.value = false;
  }
}
async function leave() {
  await api("logout", {});
  d.$reset();
  location.href = location.pathname;
  location.reload();
}
onMounted(async () => {
  try {
    const s = await api("bootstrap");
    d.demo = s.demo;
    d.promotions = s.promotions;
    if (s.role) await refresh();
  } catch (e) {
    err.value = String(e);
  } finally {
    ready.value = true;
  }
  timer = window.setInterval(() => {
    if (d.role) refresh();
  }, 4500);
});
onBeforeUnmount(() => clearInterval(timer));
watch(page, () => (mobile.value = false));
</script>
<template>
  <main v-if="!d.role" class="entry">
    <section class="entryPhoto">
      <div class="brand"><Sprout /> TableSense</div>
      <div class="entryCaption">
        <span class="eyebrow">THE BISTRO COLLECTION</span>
        <h2>Grilled steak</h2>
        <span>House pairing · Garlic mushrooms &amp; fresh lemonade</span>
      </div>
    </section>
    <section class="entryBody">
      <span class="eyebrow"><Utensils :size="15" /> Restaurant workspace</span>
      <h1>Welcome to<br /><em>TableSense.</em></h1>
      <p>
        Manage your dining floor and choose the pairings your guests see at the
        table.
      </p>
      <template v-if="ready"
        ><template v-if="d.demo && !manual"
          ><button class="primary" :disabled="busy" @click="enter('owner')">
            Enter manager demo <ArrowRight /></button
          ><button class="secondary" :disabled="busy" @click="enter('staff')">
            Enter staff demo <ArrowUpRight /></button
          ><button class="plain" @click="manual = true">
            Sign in with an account</button
          ><small
            >Demo Bistro · London · Illustrative menu and prices</small
          ></template
        >
        <form v-else @submit.prevent="enter()">
          <label
            >Username<input
              required
              autocomplete="username"
              v-model="user" /></label
          ><label
            >Password<input
              type="password"
              required
              autocomplete="current-password"
              v-model="pass" /></label
          ><button class="primary">Sign in <ArrowRight /></button></form
      ></template>
      <a class="plain" href="#/display"
        >Pair a guest display <Tablet :size="15"
      /></a>
      <p class="error" v-if="err" role="alert">{{ err }}</p>
    </section>
  </main>
  <div v-else class="shell">
    <aside :class="{ open: mobile }">
      <div class="brand"><Sprout /> TableSense</div>
      <div class="venue">
        <div class="venueIcon"><Utensils /></div>
        <div>
          <strong>{{ d.venue }}</strong
          ><small>Restaurant workspace</small>
        </div>
      </div>
      <span class="navLabel">WORKSPACE</span>
      <nav>
        <RouterLink
          v-for="s in sections.filter(
            (s) =>
              (d.role !== 'staff' || s.id === 'service') &&
              (s.id !== 'specials' || d.promotions),
          )"
          :key="s.id"
          :to="'/' + s.id"
          :class="{ selected: page === s.id }"
          ><component :is="s.icon" :size="18" />{{ s.name }}</RouterLink
        >
      </nav>
      <div class="account">
        <span class="avatar">{{ d.role.charAt(0).toUpperCase() }}</span>
        <div>
          <strong>{{
            d.role === "staff" ? "Staff workspace" : "Manager workspace"
          }}</strong
          ><small>{{ d.venue }}</small>
        </div>
        <button class="plain" aria-label="Sign out" @click="leave">
          <LogOut :size="17" />
        </button>
      </div>
    </aside>
    <div class="content">
      <header>
        <button
          class="mobileBtn plain"
          @click="mobile = !mobile"
          aria-label="Toggle navigation"
        >
          <PanelLeftClose /></button
        ><span
          >Workspace <b>/</b>
          {{ sections.find((s) => s.id === page)?.name }}</span
        ><span class="live"
          ><Radio :size="14" />{{
            d.demo ? "Pilot demo" : "Pilot service"
          }}</span
        >
      </header>
      <div class="inner">
        <p class="error" v-if="err" role="alert">{{ err }}</p>
        <Service v-if="page === 'service' || d.role === 'staff'" /><Specials
          v-else-if="page === 'specials' && d.promotions"
        /><Manager v-else :key="page" :page="page" />
      </div>
    </div>
  </div>
</template>
