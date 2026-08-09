(() => {
  const list = document.getElementById("opportunityList");
  const search = document.getElementById("search");
  const category = document.getElementById("categoryFilter");
  const verification = document.getElementById("verificationFilter");
  const availability = document.getElementById("availabilityFilter");
  const sort = document.getElementById("sort");
  const count = document.getElementById("visibleCount");
  const empty = document.getElementById("filterEmpty");
  const resetButtons = [document.getElementById("clearFilters"), document.getElementById("clearEmpty")].filter(Boolean);
  const themeToggle = document.getElementById("themeToggle");
  const freshness = document.getElementById("freshnessStatus");
  const freshnessLabel = document.getElementById("freshnessLabel");
  const freshnessDetail = document.getElementById("freshnessDetail");

  function cards() {
    return Array.from(list.querySelectorAll(".opportunity"));
  }

  function applyControls() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards().forEach((card) => {
      const matches =
        (!query || card.dataset.search.includes(query)) &&
        (category.value === "all" || card.dataset.category === category.value) &&
        (verification.value === "all" || card.dataset.verification === verification.value) &&
        (availability.value === "all" ||
          (availability.value === "for_me" && card.dataset.availability !== "unavailable") ||
          card.dataset.availability === availability.value);
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = String(visible);
    empty.hidden = visible !== 0;
  }

  function applySort() {
    const key = sort.value;
    const sorted = cards().sort((a, b) => {
      if (key === "deadline") return a.dataset.deadline.localeCompare(b.dataset.deadline);
      if (key === "prize") return Number(b.dataset.prize) - Number(a.dataset.prize);
      return Number(b.dataset.score) - Number(a.dataset.score);
    });
    sorted.forEach((card) => list.appendChild(card));
    applyControls();
  }

  [search, category, verification, availability].forEach((control) => control.addEventListener("input", applyControls));
  sort.addEventListener("change", applySort);
  resetButtons.forEach((button) => button.addEventListener("click", () => {
    search.value = "";
    category.value = "all";
    verification.value = "all";
    availability.value = "for_me";
    sort.value = "score";
    applySort();
    search.focus();
  }));

  function syncThemeLabel() {
    const dark = document.documentElement.dataset.theme === "dark";
    themeToggle.setAttribute("aria-pressed", String(dark));
    themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  themeToggle.addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme === "dark";
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    try {
      localStorage.setItem("bb-theme", dark ? "light" : "dark");
    } catch (_) {
      // Theme persistence is optional; the control still works.
    }
    syncThemeLabel();
  });
  syncThemeLabel();

  function updateFreshness() {
    if (!freshness) return;
    const generatedAt = new Date(freshness.dataset.generatedAt);
    if (Number.isNaN(generatedAt.getTime())) {
      freshness.className = "freshness stale";
      freshnessLabel.textContent = "Refresh time unavailable";
      freshnessDetail.textContent = "Treat this page as stale until the publishing pipeline runs again.";
      return;
    }
    const ageHours = Math.max(0, (Date.now() - generatedAt.getTime()) / 3600000);
    const ageDays = Math.floor(ageHours / 24);
    freshness.className = "freshness current";
    if (ageHours >= 72) {
      freshness.className = "freshness stale";
      freshnessLabel.textContent = `Data refresh is ${ageDays} days old`;
      freshnessDetail.textContent = "The publishing pipeline may be delayed. Re-check sources before acting.";
    } else if (ageHours >= 36) {
      freshness.className = "freshness delayed";
      freshnessLabel.textContent = "Refresh delayed";
      freshnessDetail.textContent = "This page is over 36 hours old. Opportunity-level check dates still apply.";
    } else {
      freshnessLabel.textContent = ageHours < 24 ? "Updated today" : "Updated yesterday";
    }
  }
  updateFreshness();
})();
