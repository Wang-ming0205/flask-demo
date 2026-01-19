(function () {
  const ctx = window.APP_CTX || {};

  function initTreeToggle() {
    const tree = document.querySelector(".tree");
    if (!tree) return;

    tree.addEventListener("click", (e) => {
      const caret = e.target.closest(".caret");
      if (!caret) return;

      // 如果點到 a，本來就要跳頁，不擋
      if (e.target.closest("a")) return;

      e.preventDefault();
      e.stopPropagation();

      const li = caret.closest("li");
      if (!li) return;
      li.classList.toggle("active");
    });
  }

  function initResetButton() {
    if (!ctx.hasResetBtn) return;

    const btn = document.getElementById("btn-reset");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const ok = await Swal.fire({
        icon: "warning",
        title: "確定要 Reset？",
        text: "會清空 DB + 刪除 uploads + 清掉 uploaded_items.json",
        showCancelButton: true,
        confirmButtonText: "我確定",
        cancelButtonText: "取消",
      });
      if (!ok.isConfirmed) return;

      try {
        const r = await fetch(ctx.resetUrl, { method: "POST" });
        const d = await r.json().catch(() => ({}));

        if (r.ok && d.success) {
          Swal.fire({ icon: "success", title: "Reset 完成", timer: 900, showConfirmButton: false });
          setTimeout(() => (window.location.href = ctx.afterResetUrl), 900);
          return;
        }
        Swal.fire({ icon: "error", title: "Reset 失敗", text: d.message || ("HTTP " + r.status) });
      } catch (err) {
        Swal.fire({ icon: "error", title: "Reset 失敗" });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTreeToggle();
    initResetButton();
  });
})();
