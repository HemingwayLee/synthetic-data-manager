// Draws a visible mouse cursor and click ripple; headless recordings don't show the real pointer.
(() => {
  if (window.top !== window || window.__tutorialCursor) return; // not inside iframes
  window.__tutorialCursor = true;
  const install = () => {
    const style = document.createElement("style");
    style.textContent = `
      #tc-cursor { position: fixed; z-index: 2147483647; pointer-events: none; width: 22px; height: 22px;
        margin: -3px 0 0 -3px; transition: transform 80ms; }
      #tc-cursor.down { transform: scale(0.85); }
      .tc-ripple { position: fixed; z-index: 2147483646; pointer-events: none; width: 44px; height: 44px;
        margin: -22px 0 0 -22px; border-radius: 50%; border: 3px solid rgba(217, 119, 87, 0.9);
        animation: tc-ripple 600ms ease-out forwards; }
      @keyframes tc-ripple { from { transform: scale(0.3); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }`;
    document.head.appendChild(style);
    const cursor = document.createElement("div");
    cursor.id = "tc-cursor";
    cursor.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7.5 19 2.6-7.4L20.5 11z"
      fill="#fff" stroke="#222" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
    cursor.style.left = "-100px";
    document.body.appendChild(cursor);
    addEventListener("mousemove", (e) => { cursor.style.left = e.clientX + "px"; cursor.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", (e) => {
      cursor.classList.add("down");
      const r = document.createElement("div");
      r.className = "tc-ripple";
      r.style.left = e.clientX + "px";
      r.style.top = e.clientY + "px";
      document.body.appendChild(r);
      setTimeout(() => r.remove(), 700);
    }, true);
    addEventListener("mouseup", () => cursor.classList.remove("down"), true);
  };
  if (document.body) install();
  else addEventListener("DOMContentLoaded", install);
})();
