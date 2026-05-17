// MyFit scan GUI — client logic.
//
// Reads bootstrap config from the global window.MYFIT_CFG that
// index.html renders, wires up the form, swatches, the SSE log
// stream, and the how-to modal.

(function () {
  const cfg = window.MYFIT_CFG || {};
  const $ = (id) => document.getElementById(id);

  const slug = (s) =>
    (s || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "") || "scan";

  // --- Auto-derived output prefix ----------------------------------------
  let prefixEdited = false;
  $("out_prefix").addEventListener("input", () => (prefixEdited = true));
  function refreshPrefix() {
    if (prefixEdited) return;
    const name = slug($("person").value);
    const d = $("scan_date").value || cfg.today;
    $("out_prefix").value =
      cfg.defaultResults + "/" + name + "_" + d.replaceAll("-", "");
  }
  ["person", "scan_date"].forEach((id) =>
    $(id).addEventListener("input", refreshPrefix),
  );
  refreshPrefix();

  // --- Colour swatches ---------------------------------------------------
  const COLOR_HEX = {
    none: null,
    red: "#d4302d",
    cyan: "#1cb6c4",
    green: "#3aa45a",
    magenta: "#c8329b",
    yellow: "#f1c33b",
    blue: "#2f6fdb",
    orange: "#e98330",
  };
  const swatchHolder = $("swatches");
  Object.entries(COLOR_HEX).forEach(([name, hex]) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "swatch" + (name === "none" ? " none" : "");
    if (hex) el.style.background = hex;
    el.title = name;
    el.dataset.value = name;
    el.addEventListener("click", () => {
      $("color").value = name;
      swatchHolder.querySelectorAll(".swatch").forEach((s) =>
        s.classList.toggle("active", s.dataset.value === name),
      );
    });
    swatchHolder.appendChild(el);
  });
  swatchHolder.firstChild.classList.add("active");

  // --- Run / cancel + SSE log stream -------------------------------------
  let evtSource = null;
  function setStatus(text, cls) {
    const s = $("status");
    s.className = "pill " + (cls || "");
    s.textContent = text;
  }

  $("form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("log").textContent = "";
    setStatus("starting", "run");
    $("run-btn").disabled = true;
    $("cancel-btn").disabled = false;
    const data = new FormData($("form"));
    const r = await fetch("/run", { method: "POST", body: data });
    const j = await r.json();
    if (!j.ok) {
      setStatus("error", "err");
      $("log").textContent = "ERROR: " + j.error + "\n";
      $("run-btn").disabled = false;
      $("cancel-btn").disabled = true;
      return;
    }
    setStatus("running", "run");
    evtSource = new EventSource("/stream");
    evtSource.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.line !== undefined) {
        $("log").textContent += m.line;
        $("log").scrollTop = $("log").scrollHeight;
      }
      if (m.done) {
        evtSource.close();
        evtSource = null;
        $("run-btn").disabled = false;
        $("cancel-btn").disabled = true;
        setStatus(
          m.rc === 0 ? "done" : "exit " + m.rc,
          m.rc === 0 ? "ok" : "err",
        );
      }
    };
  });

  $("cancel-btn").addEventListener("click", async () => {
    await fetch("/cancel", { method: "POST" });
    setStatus("cancelling", "err");
  });

  // --- How-to modal ------------------------------------------------------
  const howto = $("howto");
  const openHowto = () => {
    howto.hidden = false;
    document.body.style.overflow = "hidden";
  };
  const closeHowto = () => {
    howto.hidden = true;
    document.body.style.overflow = "";
  };
  $("howto-btn").addEventListener("click", openHowto);
  $("howto-close").addEventListener("click", closeHowto);
  howto
    .querySelector(".modal-backdrop")
    .addEventListener("click", closeHowto);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !howto.hidden) closeHowto();
  });
})();
