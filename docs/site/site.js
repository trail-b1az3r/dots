// Halcyon docs: the light/dark switch, the page list on narrow screens, and copy buttons on code.
(function () {
  "use strict";
  var root = document.documentElement;

  function systemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var dark = root.dataset.theme ? root.dataset.theme === "dark" : systemDark();
      var next = dark ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("halcyon-docs-theme", next); } catch (e) { /* private mode: just this page */ }
    });
  }

  var menu = document.querySelector(".menu-toggle");
  var sidebar = document.getElementById("sidebar");
  if (menu && sidebar) {
    menu.addEventListener("click", function () {
      var open = sidebar.classList.toggle("open");
      menu.setAttribute("aria-expanded", open ? "true" : "false");
    });
    sidebar.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        sidebar.classList.remove("open");
        menu.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll(".prose pre").forEach(function (pre) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.textContent = "Copy";
    button.addEventListener("click", function () {
      var code = pre.querySelector("code") || pre;
      var done = function () {
        button.textContent = "Copied";
        setTimeout(function () { button.textContent = "Copy"; }, 1400);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(code.innerText).then(done, function () { button.textContent = "Select it"; });
      }
    });
    pre.appendChild(button);
  });

  // Highlight the section being read in the "On this page" list.
  var links = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (links.length && "IntersectionObserver" in window) {
    var byId = {};
    links.forEach(function (a) { byId[decodeURIComponent(a.getAttribute("href").slice(1))] = a; });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && byId[entry.target.id]) {
          links.forEach(function (a) { a.classList.remove("current"); });
          byId[entry.target.id].classList.add("current");
        }
      });
    }, { rootMargin: "0px 0px -70% 0px" });
    document.querySelectorAll(".prose h2[id], .prose h3[id]").forEach(function (h) { observer.observe(h); });
  }
})();
