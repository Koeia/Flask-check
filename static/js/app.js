// Progressive enhancement for the server-rendered lookup page.
// Everything important (search, results, collapsing cards) works without this file;
// it adds the disclaimer popup, dynamic rows, autocomplete, chip picking and copy.
(function () {
  "use strict";

  const MAX_DRUGS = 20;
  const DISMISSED_KEY = "dental_disclaimer_dismissed";

  // ── Disclaimer (once per browser) ──────────────────────────────────────────
  const disclaimer = document.getElementById("disclaimer");
  if (disclaimer) {
    let dismissed = false;
    try { dismissed = !!sessionStorage.getItem(DISMISSED_KEY) || !!localStorage.getItem(DISMISSED_KEY); } catch (e) {}
    if (!dismissed) {
      disclaimer.hidden = false;
      document.getElementById("disclaimer-dismiss").focus();
    }
    document.getElementById("disclaimer-dismiss").addEventListener("click", () => {
      try { sessionStorage.setItem(DISMISSED_KEY, "1"); } catch (e) {}
      try { localStorage.setItem(DISMISSED_KEY, "1"); } catch (e) {}
      disclaimer.hidden = true;
    });
  }

  // ── Results: scroll into view + copy ───────────────────────────────────────
  const results = document.getElementById("results");
  if (results) results.scrollIntoView({ behavior: "smooth", block: "start" });

  const copyBtn = document.getElementById("copy-results");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(copyBtn.dataset.copy).then(() => {
        const idle = copyBtn.querySelector(".btn-copy__idle");
        const done = copyBtn.querySelector(".btn-copy__done");
        idle.hidden = true;
        done.hidden = false;
        copyBtn.classList.add("btn-copy--done");
        setTimeout(() => {
          idle.hidden = false;
          done.hidden = true;
          copyBtn.classList.remove("btn-copy--done");
        }, 2000);
      });
    });
  }

  // ── Medication inputs ──────────────────────────────────────────────────────
  const form = document.getElementById("lookup-form");
  if (!form) return;

  const container = document.getElementById("drug-inputs");
  const template = document.getElementById("input-row-template");
  const addBtn = document.getElementById("add-drug");
  const searchBtn = document.getElementById("search-btn");
  const names = JSON.parse(document.getElementById("drug-names").textContent);
  const generics = JSON.parse(document.getElementById("drug-generics").textContent);
  const catalog = names.map((name, i) => ({ name, generic: generics[i] || "" }));

  const inputs = () => Array.from(container.querySelectorAll(".drug-input"));

  function refresh() {
    const rows = container.querySelectorAll(".drug-input-row");
    rows.forEach((row, i) => {
      row.querySelector(".drug-input-num").textContent = i + 1;
      row.querySelector(".drug-input-remove").hidden = rows.length <= 1;
    });
    addBtn.disabled = rows.length >= MAX_DRUGS;
    searchBtn.disabled = inputs().every((el) => !el.value.trim());
    syncChips();
  }

  function addRow(value) {
    if (container.children.length >= MAX_DRUGS) return null;
    const row = template.content.firstElementChild.cloneNode(true);
    row.querySelector(".drug-input").value = value || "";
    container.appendChild(row);
    refresh();
    return row.querySelector(".drug-input");
  }

  addBtn.addEventListener("click", () => addRow("").focus());

  container.addEventListener("click", (e) => {
    const remove = e.target.closest(".drug-input-remove");
    if (remove) {
      remove.closest(".drug-input-row").remove();
      refresh();
    }
  });

  form.addEventListener("submit", () => {
    // Drop empty rows so the URL stays tidy (?drug=A&drug=B).
    inputs().forEach((el) => { if (!el.value.trim()) el.disabled = true; });
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner"></span> Looking up…';
  });

  // ── Autocomplete (filters the in-page catalog; no network round trip) ──────
  function suggestionsFor(q) {
    q = q.trim().toLowerCase();
    if (q.length < 2) return [];
    return catalog
      .filter((d) => d.name.toLowerCase().includes(q) || d.generic.toLowerCase().includes(q))
      .slice(0, 8);
  }

  function renderSuggestions(input) {
    const list = input.parentElement.querySelector(".suggestions-list");
    const matches = suggestionsFor(input.value);
    list.innerHTML = "";
    matches.forEach((d) => {
      const li = document.createElement("li");
      li.className = "suggestions-list__item";
      li.dataset.name = d.name;
      const n = document.createElement("span");
      n.className = "sug-name";
      n.textContent = d.name;
      li.appendChild(n);
      if (d.generic && d.generic.toLowerCase() !== d.name.toLowerCase()) {
        const g = document.createElement("span");
        g.className = "sug-generic";
        g.textContent = d.generic;
        li.appendChild(g);
      }
      list.appendChild(li);
    });
    list.hidden = matches.length === 0;
  }

  function hideSuggestions(input) {
    input.parentElement.querySelector(".suggestions-list").hidden = true;
  }

  function pick(input, name) {
    input.value = name;
    hideSuggestions(input);
    refresh();
  }

  container.addEventListener("input", (e) => {
    if (!e.target.matches(".drug-input")) return;
    renderSuggestions(e.target);
    refresh();
  });
  container.addEventListener("focusin", (e) => {
    if (e.target.matches(".drug-input")) renderSuggestions(e.target);
  });
  container.addEventListener("focusout", (e) => {
    if (e.target.matches(".drug-input")) setTimeout(() => hideSuggestions(e.target), 150);
  });
  container.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".suggestions-list__item");
    if (!item) return;
    e.preventDefault();
    pick(item.closest(".drug-input-wrapper").querySelector(".drug-input"), item.dataset.name);
  });

  container.addEventListener("keydown", (e) => {
    const input = e.target;
    if (!input.matches(".drug-input")) return;
    const list = input.parentElement.querySelector(".suggestions-list");
    const items = Array.from(list.children);
    const active = list.querySelector(".suggestions-list__item--active");
    let idx = items.indexOf(active);

    if (!list.hidden && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      idx = e.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
      items.forEach((li, i) => li.classList.toggle("suggestions-list__item--active", i === idx));
    } else if (e.key === "Enter" && !list.hidden && active) {
      e.preventDefault();
      pick(input, active.dataset.name);
    } else if (e.key === "Escape") {
      hideSuggestions(input);
    } else if (e.key === "Tab" && !e.shiftKey && input.value.trim()) {
      // Tab from the last filled row opens a new row (from the original TODO list).
      const all = inputs();
      if (input === all[all.length - 1] && all.length < MAX_DRUGS) {
        e.preventDefault();
        hideSuggestions(input);
        addRow("").focus();
      }
    }
  });

  // ── "Drugs in database" chips + use filter ─────────────────────────────────
  const chipList = document.getElementById("chip-list");

  function syncChips() {
    if (!chipList) return;
    const chosen = new Set(inputs().map((el) => el.value.trim().toLowerCase()).filter(Boolean));
    chipList.querySelectorAll(".chip").forEach((chip) => {
      const active = chosen.has(chip.dataset.name.toLowerCase());
      chip.classList.toggle("chip--active", active);
      chip.title = active ? "Click to remove" : "Click to add";
    });
  }

  if (chipList) {
    chipList.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      const name = chip.dataset.name;
      const lower = name.toLowerCase();
      const all = inputs();
      if (chip.classList.contains("chip--active")) {
        all.filter((el) => el.value.trim().toLowerCase() === lower).forEach((el) => {
          if (container.children.length > 1) el.closest(".drug-input-row").remove();
          else el.value = "";
        });
      } else {
        const empty = all.find((el) => !el.value.trim());
        if (empty) empty.value = name;
        else addRow(name);
      }
      refresh();
    });

    const filter = document.getElementById("drug-use-filter");
    const applyFilter = () => {
      const use = filter.value;
      chipList.querySelectorAll(".chip").forEach((chip) => {
        chip.hidden = !!use && !JSON.parse(chip.dataset.uses).includes(use);
      });
    };
    filter.addEventListener("change", applyFilter);
    document.getElementById("clear-filter").addEventListener("click", () => {
      filter.value = "";
      applyFilter();
    });
  }

  refresh();
})();
