(function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("aihub-video-form");
        if (!form) return;

        const prompt = document.getElementById("aihub-video-prompt");
        const submitBtn = document.getElementById("aihub-video-submit");
        const statusLine = document.getElementById("aihub-video-status");
        const result = document.getElementById("aihub-video-result");
        const history = document.getElementById("aihub-video-history");

        const POLL_INTERVAL_MS = 4000;
        const MAX_POLLS = 45; // ~3 minutes

        function setStatus(text, kind) {
            statusLine.textContent = text || "";
            statusLine.className = "aihub-status-line" + (kind ? " " + kind : "");
        }

        function prependHistory(videoUrl, promptText) {
            const emptyMsg = history.querySelector(".aihub-empty");
            if (emptyMsg) emptyMsg.remove();

            const item = document.createElement("div");
            item.className = "aihub-history-item";
            const video = document.createElement("video");
            video.src = videoUrl;
            video.controls = true;
            const p = document.createElement("p");
            p.textContent = promptText;
            item.appendChild(video);
            item.appendChild(p);
            history.insertBefore(item, history.firstChild);
        }

        function pollStatus(id, promptText, attempt) {
            if (attempt > MAX_POLLS) {
                setStatus("Still processing — check back on this page in a bit.", "error");
                submitBtn.disabled = false;
                prompt.disabled = false;
                return;
            }

            fetch(window.GLAB_VIDEO_STATUS_URL_TEMPLATE + id + "/status/")
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data || !data.ok) {
                        setStatus("Something went wrong checking on your video.", "error");
                        submitBtn.disabled = false;
                        prompt.disabled = false;
                        return;
                    }

                    if (data.status === "done" && data.video_url) {
                        setStatus("Done!", "success");
                        const video = document.createElement("video");
                        video.src = data.video_url;
                        video.controls = true;
                        result.innerHTML = "";
                        result.appendChild(video);
                        prependHistory(data.video_url, promptText);
                        submitBtn.disabled = false;
                        prompt.disabled = false;
                    } else if (data.status === "failed" || data.status === "not_configured") {
                        setStatus(data.error || "Video generation failed.", "error");
                        submitBtn.disabled = false;
                        prompt.disabled = false;
                    } else {
                        setStatus("Still processing… (" + data.status + ")");
                        setTimeout(function () { pollStatus(id, promptText, attempt + 1); }, POLL_INTERVAL_MS);
                    }
                })
                .catch(function () {
                    setTimeout(function () { pollStatus(id, promptText, attempt + 1); }, POLL_INTERVAL_MS);
                });
        }

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const text = prompt.value.trim();
            if (!text) return;

            submitBtn.disabled = true;
            prompt.disabled = true;
            result.innerHTML = "";
            setStatus("Submitting your video…");

            fetch(window.GLAB_VIDEO_GENERATE_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ prompt: text }),
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data && data.ok && data.id) {
                        setStatus("Queued — this can take a minute or two…");
                        pollStatus(data.id, text, 1);
                    } else {
                        setStatus((data && data.error) || "Something went wrong.", "error");
                        submitBtn.disabled = false;
                        prompt.disabled = false;
                    }
                })
                .catch(function () {
                    setStatus("Couldn't reach the server — please try again.", "error");
                    submitBtn.disabled = false;
                    prompt.disabled = false;
                });
        });
    });
})();
