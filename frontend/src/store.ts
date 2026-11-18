import { defineStore } from "pinia";
export type Item = {
  id: number;
  name: string;
  category: string;
  price: number;
  cost: number;
  available: boolean;
  active: boolean;
  image: string;
  tags: string;
  allergens: string;
  approved_until: string;
  description: string;
};
export type Card = {
  id: number;
  name: string;
  category: string;
  price: number;
  image: string;
  reason: string;
  expires: string;
  special?: boolean;
  trace?: unknown;
  status?: string;
  seen?: boolean;
  outcomes?: string[];
};
export type Table = {
  id: number;
  label: string;
  visit: number | null;
  control: boolean;
  paired: boolean;
  online: boolean;
  last_seen: string | null;
  battery: number | null;
  version: string;
  cards: Card[];
  history: Card[];
};
export const money = (p: number, currency = "GBP") =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(
    p / 100,
  );
export async function api(
  path: string,
  data?: unknown,
  method?: string,
  token?: string,
) {
  const csrf =
    document.cookie
      .split("; ")
      .find((i) => i.startsWith("csrftoken="))
      ?.split("=")[1] || "";
  const r = await fetch("/api/" + path, {
    method: method || (data === undefined ? "GET" : "POST"),
    cache: "no-store",
    credentials: token ? "omit" : "same-origin",
    signal: AbortSignal.timeout(5000),
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf,
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Connection failed" }));
    throw Error(
      typeof e === "string"
        ? e
        : e.detail || Object.values(e).flat().join(" ") || "Request failed",
    );
  }
  return r.json();
}
export const useDesk = defineStore("desk", {
  state: () => ({
    tables: [] as Table[],
    menu: [] as Item[],
    role: "",
    venue: "Demo Bistro",
    demo: false,
    promotions: false,
  }),
  actions: {
    async load() {
      const f = await api("floor");
      Object.assign(this, {
        tables: f.tables,
        menu: f.menu,
        role: f.role,
        venue: f.venue,
      });
    },
  },
});
