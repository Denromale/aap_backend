(function () {
  const stepper = document.getElementById("subStepper");
  if (!stepper) return;

  const steps = stepper.querySelectorAll(".aap-step");
  const panels = document.querySelectorAll(".aap-step-panel");

  function openPanel(code) {
    steps.forEach((s) => s.classList.remove("is-active"));
    panels.forEach((p) => p.classList.remove("is-open"));

    const activeStep = stepper.querySelector(`.aap-step[data-code="${code}"]`);
    const activePanel = document.getElementById(`panel-${code}`);

    if (activeStep) activeStep.classList.add("is-active");
    if (activePanel) activePanel.classList.add("is-open");
  }

  steps.forEach((s) => {
    s.addEventListener("click", () => openPanel(s.dataset.code));
    s.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openPanel(s.dataset.code);
    });
  });

  const params = new URLSearchParams(window.location.search);
  const open = params.get("open");

  if (open) {
    openPanel(open);
  } else {
    const first = steps[0] ? steps[0].dataset.code : null;
    if (first) openPanel(first);
  }
})();
