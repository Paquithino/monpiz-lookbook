// MonPiz lookbook, digital edition: turning the pages.
// The book is a horizontal scroller with snap points, so swiping works natively
// everywhere (Instagram's browser included). This script adds the page turn
// effect, the controls (arrows, keys, wheel), the page counter, the overview of
// all pages and links that land on a page.
(() => {
  const book = document.querySelector("[data-book]");
  if (!book) return;
  const pages = [...book.querySelectorAll(".page")];
  const numbered = pages.filter((p) => p.dataset.page);
  const counter = document.querySelector("[data-count]");
  const progress = document.querySelector("[data-progress]");
  const prev = document.querySelector("[data-prev]");
  const next = document.querySelector("[data-next]");
  const overview = document.querySelector("[data-overview]");
  const overviewToggle = document.querySelector("[data-overview-toggle]");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");

  // Pages where a turn stops: every page on phones, the first page of each spread on wide screens.
  let stops = [];
  const measure = () => {
    stops = pages.filter((p) => p.offsetParent !== null && getComputedStyle(p).scrollSnapAlign.includes("start"));
  };

  const currentStop = () => {
    const x = book.scrollLeft + book.clientWidth / 2;
    let best = 0;
    stops.forEach((p, i) => { if (p.offsetLeft <= x) best = i; });
    return best;
  };

  const goTo = (page, smooth = true) => {
    if (!page) return;
    book.scrollTo({ left: page.offsetLeft, behavior: smooth && !reduced.matches ? "smooth" : "auto" });
  };
  const turn = (step) => {
    const i = currentStop() + step;
    if (i >= 0 && i < stops.length) goTo(stops[i]);
  };

  // --- page counter, progress and address ------------------------------------------------------
  const visibleNumbers = () => {
    const left = book.scrollLeft;
    const right = left + book.clientWidth;
    return numbered
      .filter((p) => p.offsetParent !== null && p.offsetLeft >= left - 2 && p.offsetLeft < right - 2)
      .map((p) => Number(p.dataset.page));
  };
  let settleTimer;
  const update = () => {
    const shown = visibleNumbers();
    if (shown.length) {
      counter.textContent = shown.length > 1 ? `${shown[0]}–${shown[shown.length - 1]}` : String(shown[0]);
      progress.style.width = `${(shown[shown.length - 1] / numbered.length) * 100}%`;
    }
    const i = currentStop();
    prev.disabled = i === 0;
    next.disabled = i === stops.length - 1;
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      const page = stops[currentStop()];
      if (page && location.hash !== `#${page.id}`) history.replaceState(null, "", `#${page.id}`);
    }, 400);
  };

  // --- the page turn: the page that leaves rotates on its spine, the next one rises -------------
  const animate = () => {
    if (reduced.matches) return;
    const width = book.clientWidth;
    for (const page of pages) {
      const sheet = page.firstElementChild;
      const p = (page.offsetLeft - book.scrollLeft) / width; // 0 when aligned with the left edge
      if (p <= -1.05 || p >= 1.05 || page.offsetParent === null) {
        if (sheet.style.transform) { sheet.style.transform = ""; sheet.style.removeProperty("--shade"); }
        continue;
      }
      if (p < 0) {
        sheet.style.transform = `perspective(1600px) rotateY(${p * 32}deg)`;
        sheet.style.setProperty("--shade", String(-p * 0.9));
      } else {
        sheet.style.transform = `scale(${1 - Math.min(p, 1) * 0.06})`;
        sheet.style.setProperty("--shade", String(Math.min(p, 1) * 0.35));
      }
    }
  };
  // Only the leaving page turns on its spine; on wide screens the effect applies to whole spreads.
  const wide = matchMedia("(orientation: landscape) and (min-width: 900px)");
  const animateSafe = () => { if (!wide.matches) animate(); else resetTransforms(); };
  const resetTransforms = () => {
    for (const page of pages) {
      const sheet = page.firstElementChild;
      if (sheet.style.transform) { sheet.style.transform = ""; sheet.style.removeProperty("--shade"); }
    }
  };

  let ticking = false;
  book.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { animateSafe(); update(); ticking = false; });
  }, { passive: true });

  // --- controls -------------------------------------------------------------------------------
  prev.addEventListener("click", () => turn(-1));
  next.addEventListener("click", () => turn(1));
  document.addEventListener("keydown", (event) => {
    if (!overview.hidden) {
      if (event.key === "Escape") setOverview(false);
      return;
    }
    if (["ArrowRight", "PageDown", " "].includes(event.key)) { event.preventDefault(); turn(1); }
    if (["ArrowLeft", "PageUp"].includes(event.key)) { event.preventDefault(); turn(-1); }
    if (event.key === "Home") { event.preventDefault(); goTo(stops[0]); }
    if (event.key === "End") { event.preventDefault(); goTo(stops[stops.length - 1]); }
  });
  // A mouse wheel or a vertical trackpad gesture turns one page at a time.
  let wheelLock = 0;
  book.addEventListener("wheel", (event) => {
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return; // horizontal gestures scroll natively
    event.preventDefault();
    const now = Date.now();
    if (now < wheelLock || Math.abs(event.deltaY) < 4) return;
    wheelLock = now + 650;
    turn(event.deltaY > 0 ? 1 : -1);
  }, { passive: false });

  // --- overview of all pages ------------------------------------------------------------------
  const setOverview = (open) => {
    overview.hidden = !open;
    overviewToggle.setAttribute("aria-expanded", String(open));
    if (open) {
      const shown = new Set(visibleNumbers());
      let current;
      overview.querySelectorAll(".thumb").forEach((t) => {
        const page = document.getElementById(t.hash.slice(1));
        const on = page && shown.has(Number(page.dataset.page));
        t.classList.toggle("is-current", on);
        if (on && !current) current = t;
      });
      current?.scrollIntoView({ block: "center" });
      overview.querySelector("[data-overview-close]").focus();
    } else {
      overviewToggle.focus();
    }
  };
  overviewToggle.addEventListener("click", () => setOverview(overview.hidden));
  overview.querySelector("[data-overview-close]").addEventListener("click", () => setOverview(false));

  // Links to a page (contents, overview): turn to the spread that holds it.
  const spreadOf = (page) => {
    let target = page;
    for (const stop of stops) if (stop.offsetLeft <= page.offsetLeft) target = stop;
    return target;
  };
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-goto]");
    if (!link) return;
    const page = document.getElementById(link.hash.slice(1));
    if (!page) return;
    event.preventDefault();
    const fromOverview = !overview.hidden;
    if (fromOverview) setOverview(false);
    goTo(spreadOf(page), !fromOverview);
  });

  // --- colour chips: show the name of the colour touched ---------------------------------------
  for (const group of document.querySelectorAll("[data-colors]")) {
    const name = group.querySelector("[data-color-name]");
    group.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-color]");
      if (!chip) return;
      group.querySelectorAll("[data-color]").forEach((c) => {
        c.classList.toggle("is-current", c === chip);
        c.setAttribute("aria-pressed", String(c === chip));
      });
      name.textContent = chip.dataset.color;
    });
  }

  // --- start ----------------------------------------------------------------------------------
  const start = () => {
    measure();
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target && target.classList.contains("page")) goTo(spreadOf(target), false);
    update();
    animateSafe();
  };
  addEventListener("resize", () => {
    const page = stops[currentStop()];
    measure();
    goTo(page && spreadOf(page), false);
    update();
  });
  start();
  book.focus({ preventScroll: true });
})();
