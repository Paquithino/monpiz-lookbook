// MonPiz lookbook, digital edition: the top bar, the contents menu and the photo carousels.
// Everything works without JavaScript; this only adds comfort.
(() => {
  const bar = document.querySelector("[data-bar]");
  const cover = document.querySelector("[data-cover]");
  const menu = document.querySelector("[data-menu]");
  const toggle = document.querySelector("[data-menu-toggle]");

  // The bar appears once the cover has scrolled away.
  if (bar && cover && "IntersectionObserver" in window) {
    new IntersectionObserver(([entry]) => bar.classList.toggle("is-visible", !entry.isIntersecting), {
      rootMargin: "-60px 0px 0px 0px",
    }).observe(cover);
  } else if (bar) {
    bar.classList.add("is-visible");
  }

  const setMenu = (open) => {
    menu.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Chiudi" : "Indice";
    bar.classList.toggle("is-open", open);
    document.body.style.overflow = open ? "hidden" : "";
  };
  if (menu && toggle) {
    toggle.addEventListener("click", () => setMenu(menu.hidden));
    menu.addEventListener("click", (event) => {
      if (event.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !menu.hidden) {
        setMenu(false);
        toggle.focus();
      }
    });
  }

  // Carousels: the dot of the photo in view.
  for (const carousel of document.querySelectorAll("[data-carousel]")) {
    const track = carousel.querySelector(".carousel__track");
    const dots = [...carousel.querySelectorAll(".carousel__dots span")];
    const update = () => {
      const index = Math.round(track.scrollLeft / track.clientWidth);
      dots.forEach((dot, i) => dot.classList.toggle("is-current", i === index));
    };
    track.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
    update();
  }
})();
