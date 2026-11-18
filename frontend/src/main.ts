import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import Desk from "./Desk.vue";
import Display from "./Display.vue";
import "./style.css";
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/display", component: Display },
    { path: "/:page?", component: Desk },
  ],
});
createApp(App).use(createPinia()).use(router).mount("#app");
