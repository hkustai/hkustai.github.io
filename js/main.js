(function () {
  document.querySelectorAll("[data-nav-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-target") || "navbarNav";
      var panel = document.getElementById(targetId.replace(/^#/, ""));
      if (!panel) return;
      var open = panel.classList.toggle("show");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  document.querySelectorAll(".navbar a[data-value]").forEach(function (link) {
    link.addEventListener("click", function (e) {
      var id = link.getAttribute("data-value");
      if (!id) return;
      var target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      window.scrollTo({ top: target.getBoundingClientRect().top + window.pageYOffset - 100, behavior: "smooth" });
    });
  });
})();
