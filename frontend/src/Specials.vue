<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api, useDesk, money } from "./store";
const d = useDesk(),
  rows = ref<any[]>([]),
  err = ref(""),
  msg = ref(""),
  busy = ref(false);
const f = ref({
  trigger: 0,
  candidate: 0,
  pounds: 0,
  stock: 1,
  start: "",
  end: "",
  use_by_cutoff: "",
  reason: "",
  confirmed_fit: false,
  trusted_stock: false,
});
async function load() {
  rows.value = await api("promotions");
}
async function act(id?: number) {
  busy.value = true;
  err.value = msg.value = "";
  try {
    const v = f.value;
    await api(
      "promotions",
      id
        ? { withdraw: id }
        : {
            ...v,
            start: new Date(v.start).toISOString(),
            end: new Date(v.end).toISOString(),
            use_by_cutoff: new Date(v.use_by_cutoff).toISOString(),
            price: Math.round(v.pounds * 100),
          },
    );
    await load();
    msg.value = id
      ? "Special withdrawn."
      : "Special approved for the dessert stage.";
    v.confirmed_fit = v.trusted_stock = false;
  } catch (e) {
    err.value = String(e);
  } finally {
    busy.value = false;
  }
}
onMounted(() => load().catch((e) => (err.value = String(e))));
</script>
<template>
  <div class="heading">
    <div>
      <span class="eyebrow">PHASE 1.5</span>
      <h1>Approved specials</h1>
      <p>
        Approve a limited dessert pairing for a staff-signalled dessert course.
      </p>
    </div>
  </div>
  <p v-if="err" class="error">{{ err }}</p>
  <p v-if="msg" class="notice">{{ msg }}</p>
  <div v-if="rows.length" class="panel">
    <div class="line" v-for="r in rows">
      <div>
        <strong>{{ r.name }} · {{ money(r.price) }}</strong
        ><small
          >{{ r.stock }} servings ·
          {{
            r.eligible ? "Eligible" : r.withdrawn ? "Withdrawn" : "Inactive"
          }}</small
        >
      </div>
      <button
        class="secondary"
        :disabled="busy || r.withdrawn"
        @click="act(r.id)"
      >
        Withdraw
      </button>
    </div>
  </div>
  <form class="panel settings" @submit.prevent="act()">
    <h2>Approve a special</h2>
    <label
      >Ordered main<select v-model="f.trigger" required>
        <option disabled :value="0">Choose a main</option>
        <option
          v-for="i in d.menu.filter((i) => i.category === 'Main')"
          :value="i.id"
        >
          {{ i.name }}
        </option>
      </select></label
    ><label
      >Special item<select v-model="f.candidate" required>
        <option disabled :value="0">Choose an item</option>
        <option
          v-for="i in d.menu.filter((i) => i.category === 'Dessert')"
          :value="i.id"
        >
          {{ i.name }}
        </option>
      </select></label
    ><label
      >Reason for pairing<input required maxlength="160" v-model="f.reason"
    /></label>
    <div class="formgrid">
      <label
        >Approved price (£)<input
          required
          type="number"
          step=".01"
          min=".01"
          v-model.number="f.pounds" /></label
      ><label
        >Stock on hand<input
          required
          type="number"
          min="1"
          v-model.number="f.stock"
      /></label>
    </div>
    <label
      v-for="(name, k) in {
        start: 'Starts',
        end: 'Ends',
        use_by_cutoff: 'Use-by cutoff',
      }"
      >{{ name }} (local time)<input
        required
        type="datetime-local"
        v-model="f[k]" /></label
    ><label class="check"
      ><input required type="checkbox" v-model="f.confirmed_fit" />I confirm
      safe storage and suitability for sale.</label
    ><label class="check"
      ><input required type="checkbox" v-model="f.trusted_stock" />I have
      verified the available stock.</label
    ><button class="primary" :disabled="busy">Approve special</button>
  </form>
</template>
