(() => {
  const nav = document.querySelector("[data-nav]");
  const onScroll = () => {
    if (!nav) return;
    nav.classList.toggle("is-solid", window.scrollY > 24);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }

  const easeOut = (t) => 1 - Math.pow(1 - t, 3);

  const animateCount = (el) => {
    const target = Number(el.dataset.count || "0");
    const decimals = Number(el.dataset.decimals || "0");
    const duration = 1100;
    const start = performance.now();
    // survey mean stored as 416 meaning 4.16
    const displayTarget = decimals > 0 ? target / Math.pow(10, decimals) : target;

    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const value = displayTarget * easeOut(p);
      el.textContent = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString("en-US");
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  const counters = document.querySelectorAll("[data-count]");
  if ("IntersectionObserver" in window) {
    const cio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          animateCount(entry.target);
          cio.unobserve(entry.target);
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach((el) => cio.observe(el));
  } else {
    counters.forEach(animateCount);
  }
})();
