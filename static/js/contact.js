(function () {
    function showToast(text) {
        let toast = document.getElementById("glab-copy-email-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "glab-copy-email-toast";
            toast.className = "glab-copy-email-toast";
            document.body.appendChild(toast);
        }
        toast.textContent = text;
        toast.classList.add("show");
        clearTimeout(toast._hideTimer);
        toast._hideTimer = setTimeout(function () {
            toast.classList.remove("show");
        }, 2200);
    }

    function fallbackCopy(text) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        let ok = false;
        try {
            ok = document.execCommand("copy");
        } catch (e) {
            ok = false;
        }
        document.body.removeChild(textarea);
        return ok;
    }

    function copyEmail(button) {
        const email = button.getAttribute("data-email");
        if (!email) return;

        const done = function (success) {
            showToast(success ? "Email address copied!" : "Couldn't copy automatically — " + email);
            if (success) {
                button.classList.add("copied");
                setTimeout(function () { button.classList.remove("copied"); }, 1500);
            }
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(email).then(function () {
                done(true);
            }).catch(function () {
                done(fallbackCopy(email));
            });
        } else {
            done(fallbackCopy(email));
        }
    }

    document.addEventListener("click", function (e) {
        const button = e.target.closest(".glab-copy-email");
        if (button) copyEmail(button);
    });
})();
