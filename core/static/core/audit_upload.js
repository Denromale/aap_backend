(function () {
  let uploadInProgress = false;

  document.addEventListener("submit", async function (e) {
    const form = e.target;
    if (!form.matches(".js-substep-upload")) return;

    e.preventDefault();

    if (uploadInProgress) return;
    uploadInProgress = true;

    const btn = form.querySelector('button[type="submit"]');
    const originalBtnText = btn ? btn.textContent : null;

    if (btn) {
      btn.disabled = true;
      btn.textContent = "Завантаження...";
    }

    try {
      const url = form.getAttribute("action");
      const fd = new FormData(form);

      const resp = await fetch(url, {
        method: "POST",
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });

      const data = await resp.json();

      if (!data.ok) {
        alert(data.error || "Upload error");
        uploadInProgress = false;
        if (btn) {
          btn.disabled = false;
          btn.textContent = originalBtnText || "Завантажити";
        }
        return;
      }

      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Помилка завантаження");
      uploadInProgress = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalBtnText || "Завантажити";
      }
    }
  });
})();
