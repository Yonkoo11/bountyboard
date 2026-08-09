(() => {
  const list = document.getElementById("opportunityList");
  const search = document.getElementById("search");
  const category = document.getElementById("categoryFilter");
  const availability = document.getElementById("availabilityFilter");
  const sort = document.getElementById("sort");
  const count = document.getElementById("visibleCount");
  const empty = document.getElementById("filterEmpty");
  const viewButtons = Array.from(document.querySelectorAll("[data-view]"));
  const resetButtons = [document.getElementById("clearFilters"), document.getElementById("clearEmpty")].filter(Boolean);
  const themeToggle = document.getElementById("themeToggle");
  const freshness = document.getElementById("freshnessStatus");
  const freshnessLabel = document.getElementById("freshnessLabel");
  const freshnessDetail = document.getElementById("freshnessDetail");
  let activeView = "actionable";

  const cards = () => Array.from(list.querySelectorAll(".opportunity"));

  function applyControls() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards().forEach((card) => {
      const viewMatch = activeView === "all" ||
        (activeView === "actionable" && card.dataset.actionable === "true") ||
        (activeView === "research" && card.dataset.research === "true");
      const availabilityMatch = availability.value === "all" ||
        (availability.value === "for_me" && card.dataset.availability !== "unavailable") ||
        card.dataset.availability === availability.value;
      const matches = viewMatch && availabilityMatch &&
        (!query || card.dataset.search.includes(query)) &&
        (category.value === "all" || card.dataset.category === category.value);
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = String(visible);
    empty.hidden = visible !== 0;
  }

  function applySort() {
    const sorted = cards().sort((a, b) => {
      if (sort.value === "deadline") return a.dataset.deadline.localeCompare(b.dataset.deadline);
      if (sort.value === "prize") return Number(b.dataset.prize) - Number(a.dataset.prize);
      return Number(b.dataset.score) - Number(a.dataset.score);
    });
    sorted.forEach((card) => list.appendChild(card));
    applyControls();
  }

  viewButtons.forEach((button) => button.addEventListener("click", () => {
    activeView = button.dataset.view;
    viewButtons.forEach((item) => item.classList.toggle("active", item === button));
    applyControls();
  }));
  [search, category, availability].forEach((control) => control.addEventListener("input", applyControls));
  sort.addEventListener("change", applySort);
  resetButtons.forEach((button) => button.addEventListener("click", () => {
    activeView = "actionable";
    viewButtons.forEach((item) => item.classList.toggle("active", item.dataset.view === activeView));
    search.value = "";
    category.value = "all";
    availability.value = "for_me";
    sort.value = "score";
    applySort();
  }));

  function syncThemeLabel() {
    const dark = document.documentElement.dataset.theme === "dark";
    themeToggle.setAttribute("aria-pressed", String(dark));
    themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }
  themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("bb-theme", next); } catch (_) { /* persistence is optional */ }
    syncThemeLabel();
  });
  syncThemeLabel();

  function updateFreshness() {
    const generatedAt = new Date(freshness.dataset.generatedAt);
    if (Number.isNaN(generatedAt.getTime())) {
      freshness.className = "freshness stale";
      freshnessLabel.textContent = "Refresh time unavailable";
      freshnessDetail.textContent = "Treat this page as stale until publishing succeeds.";
      return;
    }
    const ageHours = Math.max(0, (Date.now() - generatedAt.getTime()) / 3600000);
    freshness.className = ageHours >= 72 ? "freshness stale" : ageHours >= 36 ? "freshness delayed" : "freshness current";
    if (ageHours >= 72) freshnessLabel.textContent = `Data refresh is ${Math.floor(ageHours / 24)} days old`;
    else if (ageHours >= 36) freshnessLabel.textContent = "Refresh delayed";
    else freshnessLabel.textContent = ageHours < 24 ? "Updated today" : "Updated yesterday";
  }
  updateFreshness();
  applySort();
})();
