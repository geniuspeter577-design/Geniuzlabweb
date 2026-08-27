(function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("aihub-image-form");
        if (!form) return;

        const prompt = document.getElementById("aihub-image-prompt");
        const submitBtn = document.getElementById("aihub-image-submit");
        const statusLine = document.getElementById("aihub-image-status");
        const result = document.getElementById("aihub-image-result");
        const history = document.getElementById("aihub-image-history");

        function setStatus(text, kind) {
            statusLine.textContent = text || "";
            statusLine.className = "aihub-status-line" + (kind ? " " + kind : "");
        }

        function prependHistory(imageUrl, promptText) {
            const emptyMsg = history.querySelector(".aihub-empty");
            if (emptyMsg) emptyMsg.remove();

            const item = document.createElement("div");
            item.className = "aihub-history-item";
            const img = document.createElement("img");
            img.src = imageUrl;
            img.alt = promptText;
            const p = document.createElement("p");
            p.textContent = promptText;
            item.appendChild(img);
            item.appendChild(p);
            history.insertBefore(item, history.firstChild);
        }

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const text = prompt.value.trim();
            if (!text) return;

            submitBtn.disabled = true;
            prompt.disabled = true;
            result.innerHTML = "";
            setStatus("Generating your image…");

            fetch(window.GLAB_IMAGE_GENERATE_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ prompt: text }),
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data && data.ok && data.image_url) {
                        setStatus("Done!", "success");
                        const img = document.createElement("img");
                        img.src = data.image_url;
                        img.alt = text;
                        result.appendChild(img);
                        prependHistory(data.image_url, text);
                    } else {
                        setStatus((data && data.error) || "Something went wrong.", "error");
                    }
                })
                .catch(function () {
                    setStatus("Couldn't reach the server — please try again.", "error");
                })
                .finally(function () {
                    submitBtn.disabled = false;
                    prompt.disabled = false;
                });
        });
    });
})();
