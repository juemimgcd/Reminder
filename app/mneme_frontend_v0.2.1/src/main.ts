import { createApp } from "vue";
import App from "./App.vue";
import { initializePreferences } from "./composables/usePreferences";
import "./index.css";

initializePreferences();
createApp(App).mount("#root");
