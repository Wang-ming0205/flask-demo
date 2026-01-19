(function () {
  "use strict";

  // 從 template 注入的設定（外部 js 不能寫 Jinja）
  const CFG = window.EQUIPMENT_UPLOAD_CFG || {};
  const ADD_LOCATION_URL = CFG.addLocationUrl || "";
  const UPLOAD_URL = CFG.uploadUrl || ""; // 目前用不到（我們用 form.action），留著未來可用

  function syncUploadUI() {
    const cat = (document.getElementById("file-category")?.value || "inspection").toLowerCase();

    const fbWrap = document.getElementById("feedback-wrapper");
    const fbText = document.querySelector('textarea[name="feedback_text"]');
    const fileInput = document.getElementById("file-input");

    const eqWrap = document.getElementById("equipment-id-wrapper");
    const eqSel = document.getElementById("equipment-id");

    // feedback：顯示文字、檔案不必填、設備不需要
    if (cat === "feedback") {
      if (fbWrap) fbWrap.style.display = "";
      if (fbText) fbText.required = true;

      if (fileInput) {
        fileInput.value = "";
        fileInput.required = false;
      }

      if (eqWrap) eqWrap.style.display = "none";
      if (eqSel) eqSel.value = "";
      return;
    }

    // 非 feedback：隱藏 feedback、檔案必填
    if (fbWrap) fbWrap.style.display = "none";
    if (fbText) fbText.required = false;
    if (fileInput) fileInput.required = true;

    // logs：顯示設備選單且必填
    if (cat === "logs") {
      if (eqWrap) eqWrap.style.display = "";
      if (eqSel) eqSel.required = true;
    } else {
      if (eqWrap) eqWrap.style.display = "none";
      if (eqSel) {
        eqSel.required = false;
        eqSel.value = "";
      }
    }
  }

  function bindAddLocation() {
    const btn = document.getElementById("add-location-btn");
    if (!btn) return;

    btn.addEventListener("click", async (e) => {
      e.preventDefault();

      const country = (document.getElementById("country-input")?.value || "").trim();
      const room = (document.getElementById("room-input")?.value || "").trim();

      if (!country) {
        window.Swal
          ? Swal.fire({ icon: "warning", title: "至少要輸入國家/地點" })
          : alert("至少要輸入國家/地點");
        return;
      }

      if (!ADD_LOCATION_URL) {
        window.Swal
          ? Swal.fire({ icon: "error", title: "新增失敗", text: "ADD_LOCATION_URL 未設定" })
          : alert("ADD_LOCATION_URL 未設定");
        return;
      }

      try {
        if (window.Swal) {
          Swal.fire({
            title: "新增中...",
            allowOutsideClick: false,
            showConfirmButton: false,
            didOpen: () => Swal.showLoading(),
          });
        }

        const resp = await fetch(ADD_LOCATION_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ country, room }),
        });

        const d = await resp.json();
        if (!resp.ok || !d.success) throw new Error(d.message || `HTTP ${resp.status}`);

        if (window.Swal) {
          await Swal.fire({ icon: "success", title: "新增完成", timer: 900, showConfirmButton: false });
        }

        // 你原本的導向邏輯：有 room 就去 room upload
        if (d.country_id && d.room_id) {
          window.location.href = `/case-scenes/${d.country_id}/rooms/${d.room_id}/equipments?mode=upload`;
          return;
        }
        if (d.country_id) {
          window.location.href = `/case-scenes/${d.country_id}`;
          return;
        }
        window.location.href = "/";
      } catch (err) {
        console.error(err);
        window.Swal
          ? Swal.fire({ icon: "error", title: "新增失敗", text: err?.message || "" })
          : alert("新增失敗");
      }
    });
  }

  function bindUpload() {
    const form = document.getElementById("upload-form");
    if (!form) return;

    const wrap = document.getElementById("upload-progress-wrapper");
    const bar = document.getElementById("swal-progress");
    const pct = document.getElementById("swal-percent");
    const done = document.getElementById("upload-complete-message");

    const eqSel = document.getElementById("equipment-id");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      syncUploadUI();

      const countryVal = (document.getElementById("country-input")?.value || "").trim();
      const roomVal = (document.getElementById("room-input")?.value || "").trim();
      const cat = (document.getElementById("file-category")?.value || "inspection").toLowerCase();

      if (!countryVal) {
        window.Swal ? Swal.fire({ icon: "warning", title: "請先輸入國家/地點" }) : alert("請先輸入國家/地點");
        return;
      }

      if (!roomVal && ["inspection", "logs", "feedback"].includes(cat)) {
        window.Swal ? Swal.fire({ icon: "warning", title: "請先選擇 / 輸入 Room" }) : alert("請先選擇 / 輸入 Room");
        return;
      }

      if (cat === "logs") {
        const eqId = (eqSel?.value || "").trim();
        if (!eqId) {
          window.Swal ? Swal.fire({ icon: "error", title: "Logs 必須選擇設備" }) : alert("Logs 必須選擇設備");
          return;
        }
      }

      // 把乾淨值寫回去，確保 FormData 送的就是 trim 後的
      document.getElementById("country-input").value = countryVal;
      document.getElementById("room-input").value = roomVal;

      const fd = new FormData(form);

      if (wrap) wrap.style.display = "flex";
      if (bar) bar.style.width = "0%";
      if (pct) pct.textContent = "0%";
      if (done) done.style.display = "none";

      const xhr = new XMLHttpRequest();
      xhr.open("POST", form.action); // 用 form.action 最穩

      xhr.upload.onprogress = (evt) => {
        if (!evt.lengthComputable) return;
        const p = Math.round((evt.loaded / evt.total) * 100);
        if (bar) bar.style.width = `${p}%`;
        if (pct) pct.textContent = `${p}%`;
      };

      xhr.onload = async () => {
        let d = null;
        try {
          d = JSON.parse(xhr.responseText);
        } catch {}

        if (xhr.status >= 200 && xhr.status < 300 && d?.success) {
          if (done) done.style.display = "block";
          if (window.Swal) await Swal.fire({ icon: "success", title: "上傳完成", timer: 900, showConfirmButton: false });
          window.location.reload();
          return;
        }

        const msg = d?.message || `HTTP ${xhr.status}`;
        window.Swal ? Swal.fire({ icon: "error", title: "上傳失敗", text: msg }) : alert(`上傳失敗: ${msg}`);
      };

      xhr.onerror = () => {
        window.Swal ? Swal.fire({ icon: "error", title: "上傳失敗" }) : alert("上傳失敗");
      };

      xhr.send(fd);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    // 只要不是 upload 頁（沒有 form）就直接不做事
    if (!document.getElementById("upload-form")) return;

    document.getElementById("file-category")?.addEventListener("change", syncUploadUI);
    syncUploadUI();
    bindAddLocation();
    bindUpload();
  });
})();
