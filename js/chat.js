(() => {
  const log = document.getElementById("chatLog");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("question");
  const sendBtn = document.getElementById("sendBtn");
  const pill = document.getElementById("statusPill");
  const suggestions = document.getElementById("suggestions");

  const addBubble = (role, text, extraClass = "") => {
    const el = document.createElement("div");
    el.className = `bubble ${role} ${extraClass}`.trim();
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  };

  addBubble(
    "system",
    "Welcome. Ask an educational question — ECHO will use the same PubMed / prior-session pipeline as the Zoom assistant."
  );

  const setStatus = (state, label) => {
    pill.dataset.state = state;
    pill.textContent = label;
  };

  const refreshStatus = async () => {
    try {
      const res = await fetch("/api/status", { cache: "no-store" });
      const data = await res.json();
      if (data.ready) {
        setStatus("ready", "AI ready");
      } else if (data.bot?.ok) {
        setStatus("down", "AI warming up");
      } else {
        setStatus("down", "Backend offline");
      }
    } catch {
      setStatus("down", "Backend offline");
    }
  };

  refreshStatus();
  setInterval(refreshStatus, 15000);

  suggestions?.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-q]");
    if (!btn) return;
    input.value = btn.getAttribute("data-q") || "";
    input.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    addBubble("user", question);
    input.value = "";
    sendBtn.disabled = true;
    const pending = addBubble("assistant", "Thinking", "typing");

    const started = performance.now();
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      const ms = Math.round(performance.now() - started);
      pending.classList.remove("typing");

      if (!data.ok || !data.answer) {
        pending.classList.add("error");
        pending.textContent = data.error || "No answer returned. The AI services may still be starting.";
        return;
      }

      pending.textContent = data.answer;
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = data.latencyMs ? `${data.latencyMs} ms` : `${ms} ms`;
      pending.appendChild(meta);
      setStatus("ready", "AI ready");
    } catch (err) {
      pending.classList.remove("typing");
      pending.classList.add("error");
      pending.textContent = `Request failed: ${err?.message || err}`;
      setStatus("down", "Backend offline");
    } finally {
      sendBtn.disabled = false;
      input.focus();
      log.scrollTop = log.scrollHeight;
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
})();
