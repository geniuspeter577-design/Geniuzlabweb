/*
 * Progressively enhances any <select data-glab-select> into a custom
 * dropdown that shows a colored network/provider badge next to each
 * option (and on the closed trigger), instead of the browser's plain
 * native control. The original <select> stays in the DOM and keeps
 * receiving `.value` updates + a real `change` event on every pick, so
 * any existing form logic, validation, or JS listeners built around it
 * keep working untouched.
 */
(function () {
    // value -> { label, color, text } used to render the badge. Falls
    // back to a neutral badge with the option's first letter for any
    // choice not listed here, so new choices never render broken.
    const BADGE_MAP = {
        "mtn": { color: "#FFCB05", text: "#171300" },
        "mtn-data": { color: "#FFCB05", text: "#171300" },
        "glo": { color: "#00A651", text: "#ffffff" },
        "glo-data": { color: "#00A651", text: "#ffffff" },
        "airtel": { color: "#ED1C24", text: "#ffffff" },
        "airtel-data": { color: "#ED1C24", text: "#ffffff" },
        "etisalat": { color: "#00A99D", text: "#ffffff" },
        "etisalat-data": { color: "#00A99D", text: "#ffffff" },
        "dstv": { color: "#0A3A8C", text: "#ffffff" },
        "gotv": { color: "#8DC63F", text: "#12210a" },
        "startimes": { color: "#E4032E", text: "#ffffff" },
    };
    const DEFAULT_BADGE = { color: "#7ED957", text: "#06130c" };

    function badgeFor(value, label) {
        const cfg = BADGE_MAP[value];
        const initial = (label || "?").trim().charAt(0).toUpperCase();
        return {
            initial: initial || "?",
            color: cfg ? cfg.color : DEFAULT_BADGE.color,
            text: cfg ? cfg.text : DEFAULT_BADGE.text,
        };
    }

    function enhanceSelect(select) {
        if (select.dataset.glabEnhanced) return;
        select.dataset.glabEnhanced = "1";

        const wrapper = document.createElement("div");
        wrapper.className = "glab-select";
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);
        select.classList.add("glab-select-native");
        select.setAttribute("aria-hidden", "true");
        select.tabIndex = -1;

        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "glab-select-trigger";
        wrapper.appendChild(trigger);

        const panel = document.createElement("div");
        panel.className = "glab-select-panel";
        wrapper.appendChild(panel);

        function renderTrigger() {
            const opt = select.options[select.selectedIndex];
            const label = opt ? opt.textContent.trim() : "Select…";
            const badge = badgeFor(select.value, label);
            trigger.innerHTML =
                '<span class="glab-select-badge" style="background:' + badge.color + ";color:" + badge.text + '">' + badge.initial + "</span>" +
                '<span class="glab-select-label">' + label + "</span>" +
                '<i class="fas fa-chevron-down glab-select-caret"></i>';
        }

        function renderPanel() {
            panel.innerHTML = "";
            Array.from(select.options).forEach(function (opt) {
                const label = opt.textContent.trim();
                if (!opt.value && !label) return;
                const badge = badgeFor(opt.value, label);
                const item = document.createElement("button");
                item.type = "button";
                item.className = "glab-select-option" + (opt.value === select.value ? " active" : "");
                item.innerHTML =
                    '<span class="glab-select-badge" style="background:' + badge.color + ";color:" + badge.text + '">' + badge.initial + "</span>" +
                    "<span>" + label + "</span>";
                item.addEventListener("click", function () {
                    if (select.value !== opt.value) {
                        select.value = opt.value;
                        select.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                    renderTrigger();
                    closePanel();
                });
                panel.appendChild(item);
            });
        }

        function openPanel() {
            renderPanel();
            panel.classList.add("open");
            trigger.classList.add("open");
        }

        function closePanel() {
            panel.classList.remove("open");
            trigger.classList.remove("open");
        }

        trigger.addEventListener("click", function (e) {
            e.stopPropagation();
            if (panel.classList.contains("open")) {
                closePanel();
            } else {
                openPanel();
            }
        });

        document.addEventListener("click", function (e) {
            if (!wrapper.contains(e.target)) closePanel();
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") closePanel();
        });

        renderTrigger();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("select[data-glab-select]").forEach(enhanceSelect);
    });
})();
