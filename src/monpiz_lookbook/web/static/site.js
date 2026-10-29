// MonPiz lookbook, digital edition: page counter, previous/next page, overview of
// all pages, colour names. The pages scroll down natively; this only adds comfort.
(() => {
  const pages = [...document.querySelectorAll("[data-page]")];
  if (!pages.length) return;
  const counter = document.querySelector("[data-count]");
  const progress = document.querySelector("[data-progress]");
  const prev = document.querySelector("[data-prev]");
  const next = document.querySelector("[data-next]");
  const overview = document.querySelector("[data-overview]");
  const overviewToggle = document.querySelector("[data-overview-toggle]");

  // The current page is the one crossing the upper third of the screen.
  const current = () => {
    const line = innerHeight / 3;
    let index = 0;
    pages.forEach((page, i) => { if (page.getBoundingClientRect().top <= line) index = i; });
    return index;
  };
  const show = (page) => page?.scrollIntoView({ block: "start" });

  let settle;
  const update = () => {
    const i = current();
    counter.textContent = String(i + 1);
    progress.style.width = `${((i + 1) / pages.length) * 100}%`;
    prev.disabled = i === 0;
    next.disabled = i === pages.length - 1;
    clearTimeout(settle);
    settle = setTimeout(() => {
      const id = pages[current()].id;
      if (location.hash !== `#${id}`) history.replaceState(null, "", `#${id}`);
    }, 300);
  };
  // The page controls step aside while reading down and come back when scrolling up.
  const dock = document.querySelector(".dock");
  let lastY = scrollY;
  let ticking = false;
  addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const y = scrollY;
      if (Math.abs(y - lastY) > 8) {
        dock.classList.toggle("is-away", y > lastY && y > innerHeight / 2);
        lastY = y;
      }
      update();
      ticking = false;
    });
  }, { passive: true });
  addEventListener("resize", update);

  prev.addEventListener("click", () => show(pages[current() - 1]));
  next.addEventListener("click", () => show(pages[current() + 1]));

  // --- overview of all pages ------------------------------------------------------------------
  const setOverview = (open) => {
    overview.hidden = !open;
    overviewToggle.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      const id = pages[current()].id;
      let here;
      overview.querySelectorAll(".thumb").forEach((t) => {
        const on = t.hash === `#${id}`;
        t.classList.toggle("is-current", on);
        if (on) here = t;
      });
      here?.scrollIntoView({ block: "center" });
      overview.querySelector("[data-overview-close]").focus();
    } else {
      overviewToggle.focus({ preventScroll: true });
    }
  };
  overviewToggle.addEventListener("click", () => setOverview(overview.hidden));
  overview.querySelector("[data-overview-close]").addEventListener("click", () => setOverview(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !overview.hidden) setOverview(false);
  });

  // Links to a page (contents, overview, cover): close the overview and jump there.
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-goto]");
    if (!link) return;
    const page = document.getElementById(link.hash.slice(1));
    if (!page) return;
    event.preventDefault();
    const fromOverview = !overview.hidden;
    if (fromOverview) setOverview(false);
    page.scrollIntoView({ block: "start", behavior: fromOverview ? "auto" : "smooth" });
  });

  // --- colour chips: show the name of the colour touched ---------------------------------------
  for (const group of document.querySelectorAll("[data-colors]")) {
    group.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-color]");
      if (!chip) return;
      group.querySelectorAll("[data-color]").forEach((c) => {
        c.classList.toggle("is-current", c === chip);
        c.setAttribute("aria-pressed", String(c === chip));
      });
    });
  }

  update();
})();
