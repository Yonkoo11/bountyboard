(() => {
  const list = document.getElementById("opportunityList");
  const search = document.getElementById("search");
  const category = document.getElementById("categoryFilter");
  const verification = document.getElementById("verificationFilter");
  const sort = document.getElementById("sort");
  const count = document.getElementById("visibleCount");
  const empty = document.getElementById("filterEmpty");
  const resetButtons = [document.getElementById("clearFilters"), document.getElementById("clearEmpty")].filter(Boolean);
  const themeToggle = document.getElementById("themeToggle");

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
        (verification.value === "all" || card.dataset.verification === verification.value);
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

  [search, category, verification].forEach((control) => control.addEventListener("input", applyControls));
  sort.addEventListener("change", applySort);
  resetButtons.forEach((button) => button.addEventListener("click", () => {
    search.value = "";
    category.value = "all";
    verification.value = "all";
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
})();
