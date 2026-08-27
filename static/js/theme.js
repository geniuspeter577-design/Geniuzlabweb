(function () {
  "use strict";

  var STORAGE_KEY = "gl-theme";
  var root = document.documentElement;

  function currentTheme() {
    return root.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function applyIcons(theme) {
    // Icon shows what you'd switch TO, which is the usual convention
    // for a single toggle button (moon while light, sun while dark).
    var iconClass = theme === "light" ? "fas fa-sun" : "fas fa-moon";
    var label = theme === "light" ? "Light mode" : "Dark mode";

    var desktopIcon = document.getElementById("gl-theme-icon");
    if (desktopIcon) desktopIcon.className = iconClass;

    var mobileIcon = document.getElementById("gl-theme-icon-mobile");
    if (mobileIcon) mobileIcon.className = iconClass;

    var mobileLabel = document.getElementById("gl-theme-label-mobile");
    if (mobileLabel) mobileLabel.textContent = label;
  }

  function setTheme(theme, persist) {
    if (theme === "light") {
      root.setAttribute("data-theme", "light");
    } else {
      root.removeAttribute("data-theme");
      theme = "dark";
    }
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) { /* ignore */ }
    }
    applyIcons(theme);
  }

  function toggle() {
    setTheme(currentTheme() === "light" ? "dark" : "light", true);
  }

  document.addEventListener("DOMContentLoaded", function () {
    // The inline head script already set data-theme before first paint;
    // this just syncs the icon/label to whatever it landed on.
    applyIcons(currentTheme());

    var desktopBtn = document.getElementById("gl-theme-toggle");
    if (desktopBtn) desktopBtn.addEventListener("click", toggle);

    var mobileBtn = document.getElementById("gl-theme-toggle-mobile");
    if (mobileBtn) mobileBtn.addEventListener("click", toggle);
  });
})();
