/* NEXORA interaction layer: sidebar, password reveal, confirms, charts, alerts. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initPasswordToggle();
    initAutoSubmit();
    initConfirmModal();
    initAlerts();
    initTooltips();
    initChartDefaults();
  });

  /* ------------------------------------------------------------------ */
  /* Mobile sidebar                                                     */
  /* ------------------------------------------------------------------ */
  function initSidebar() {
    var toggle = document.querySelector("[data-sidebar-toggle]");
    var sidebar = document.querySelector("[data-sidebar]");
    var backdrop = document.querySelector("[data-sidebar-backdrop]");
    if (!toggle || !sidebar) return;

    function close() {
      sidebar.classList.remove("is-open");
      if (backdrop) backdrop.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", function () {
      var open = sidebar.classList.toggle("is-open");
      if (backdrop) backdrop.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    if (backdrop) backdrop.addEventListener("click", close);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
    });
  }

  /* ------------------------------------------------------------------ */
  /* Show / hide password                                               */
  /* ------------------------------------------------------------------ */
  function initPasswordToggle() {
    document.querySelectorAll("[data-pw-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.getAttribute("data-pw-toggle"));
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        button.setAttribute("aria-pressed", show ? "true" : "false");
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        var on = button.querySelector("[data-icon-show]");
        var off = button.querySelector("[data-icon-hide]");
        if (on) on.style.display = show ? "none" : "block";
        if (off) off.style.display = show ? "block" : "none";
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Filter selects submit their form on change                         */
  /* ------------------------------------------------------------------ */
  function initAutoSubmit() {
    document.querySelectorAll("[data-autosubmit]").forEach(function (field) {
      field.addEventListener("change", function () {
        if (field.form) field.form.submit();
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Destructive action confirmation                                    */
  /* ------------------------------------------------------------------ */
  function initConfirmModal() {
    var modal = document.getElementById("nxConfirm");
    if (!modal) return;

    var form = modal.querySelector("form");
    var titleEl = modal.querySelector("[data-confirm-title]");
    var textEl = modal.querySelector("[data-confirm-text]");
    var actionEl = modal.querySelector("[data-confirm-action]");
    var lastFocus = null;

    function open(trigger) {
      var url = trigger.getAttribute("data-confirm-url");
      if (!url) return;
      lastFocus = trigger;
      form.setAttribute("action", url);
      titleEl.textContent = trigger.getAttribute("data-confirm-title") || "Are you sure?";
      textEl.textContent =
        trigger.getAttribute("data-confirm-text") ||
        "This action cannot be undone.";
      if (actionEl) {
        actionEl.textContent = trigger.getAttribute("data-confirm-action") || "Delete";
      }
      modal.hidden = false;
      document.body.style.overflow = "hidden";
      var focusTarget = modal.querySelector("[data-confirm-cancel]");
      if (focusTarget) focusTarget.focus();
    }

    function close() {
      modal.hidden = true;
      document.body.style.overflow = "";
      if (lastFocus) lastFocus.focus();
    }

    document.querySelectorAll("[data-confirm-url]").forEach(function (trigger) {
      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        open(trigger);
      });
    });

    modal.querySelectorAll("[data-confirm-cancel], [data-confirm-close]").forEach(function (el) {
      el.addEventListener("click", function (event) {
        event.preventDefault();
        close();
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) close();
    });
  }

  /* ------------------------------------------------------------------ */
  /* Dismissible alerts                                                 */
  /* ------------------------------------------------------------------ */
  function initAlerts() {
    document.querySelectorAll("[data-alert-close]").forEach(function (button) {
      button.addEventListener("click", function () {
        var alert = button.closest(".nx-alert");
        if (alert) alert.remove();
      });
    });

    document.querySelectorAll(".nx-alert[data-autohide]").forEach(function (alert) {
      window.setTimeout(function () {
        alert.style.transition = "opacity .35s ease, transform .35s ease";
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-6px)";
        window.setTimeout(function () {
          alert.remove();
        }, 380);
      }, 6500);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Bootstrap tooltips                                                 */
  /* ------------------------------------------------------------------ */
  function initTooltips() {
    if (!window.bootstrap || !window.bootstrap.Tooltip) return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      new window.bootstrap.Tooltip(el, { placement: "top", trigger: "hover" });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Shared Chart.js look & feel                                        */
  /* ------------------------------------------------------------------ */
  function initChartDefaults() {
    if (!window.Chart) return;
    var Chart = window.Chart;
    Chart.defaults.font.family =
      "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif";
    Chart.defaults.font.size = 11.5;
    Chart.defaults.color = "#718078";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 7;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.plugins.legend.labels.font = { size: 11.5, weight: "500" };
    Chart.defaults.plugins.tooltip.backgroundColor = "#0B211D";
    Chart.defaults.plugins.tooltip.padding = 11;
    Chart.defaults.plugins.tooltip.cornerRadius = 9;
    Chart.defaults.plugins.tooltip.titleFont = { size: 12, weight: "600" };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.boxWidth = 7;
    Chart.defaults.plugins.tooltip.boxHeight = 7;
    Chart.defaults.elements.bar.borderRadius = 7;
    Chart.defaults.elements.bar.borderSkipped = false;
  }

  /* Exposed helpers used by the dashboard / report templates */
  window.NexoraCharts = {
    palette: ["#003B35", "#26866C", "#DDE9D5", "#D99A42", "#718078", "#0B211D", "#8FB79B"],
    grid: "rgba(220,227,218,0.8)",
    read: function (id) {
      var el = document.getElementById(id);
      if (!el) return null;
      try {
        return JSON.parse(el.textContent);
      } catch (error) {
        return null;
      }
    },
    empty: function (canvasId, message) {
      var canvas = document.getElementById(canvasId);
      if (!canvas || !canvas.parentElement) return;
      var box = canvas.parentElement;
      box.innerHTML = "";
      var wrapper = document.createElement("div");
      wrapper.className = "nx-chart-empty";
      wrapper.textContent = message || "No data for this period yet.";
      box.appendChild(wrapper);
    }
  };
})();
