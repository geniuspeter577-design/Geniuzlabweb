(function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const launcher = document.getElementById("glab-assistant-launcher");
        const panel = document.getElementById("glab-assistant-panel");
        const closeBtn = document.getElementById("glab-assistant-close");
        const form = document.getElementById("glab-assistant-form");
        const input = document.getElementById("glab-assistant-input");
        const sendBtn = form ? form.querySelector("button[type='submit']") : null;
        const messages = document.getElementById("glab-assistant-messages");

        if (!launcher || !panel || !form) return;

        function appendMessage(text, who) {
            const el = document.createElement("div");
            el.className = "glab-msg " + (who === "user" ? "glab-msg-user" : "glab-msg-bot");
            el.textContent = text;
            messages.appendChild(el);
            messages.scrollTop = messages.scrollHeight;
            return el;
        }

        function appendLinks(links) {
            if (!links || !links.length) return;
            const usable = links.filter(function (l) {
                return l && l.url && l.url !== "#";
            });
            if (!usable.length) return;
            const wrap = document.createElement("div");
            wrap.className = "glab-msg-links";
            usable.forEach(function (l) {
                const a = document.createElement("a");
                a.href = l.url;
                a.textContent = l.label;
                wrap.appendChild(a);
            });
            messages.appendChild(wrap);
            messages.scrollTop = messages.scrollHeight;
        }

        // Quick-reply chips are tappable canned answers (e.g. "Yes, I have
        // an account") that feed straight back into the conversation, as
        // opposed to `links`, which navigate away to another page.
        function appendQuickReplies(replies) {
            if (!replies || !replies.length) return;
            const wrap = document.createElement("div");
            wrap.className = "glab-quick-replies";
            replies.forEach(function (label) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "glab-quick-reply";
                btn.textContent = label;
                btn.addEventListener("click", function () {
                    wrap.remove();
                    sendMessage(label);
                });
                wrap.appendChild(btn);
            });
            messages.appendChild(wrap);
            messages.scrollTop = messages.scrollHeight;
        }

        function handleRedirect(url) {
            if (!url) return;
            const note = document.createElement("div");
            note.className = "glab-msg glab-msg-bot glab-msg-redirect";
            note.textContent = "Connecting you to WhatsApp…";
            messages.appendChild(note);
            messages.scrollTop = messages.scrollHeight;
            setTimeout(function () {
                window.location.href = url;
            }, 2000);
        }

        function showTyping() {
            const el = document.createElement("div");
            el.className = "glab-msg glab-msg-bot glab-typing";
            el.id = "glab-typing-indicator";
            el.innerHTML = "<span></span><span></span><span></span>";
            messages.appendChild(el);
            messages.scrollTop = messages.scrollHeight;
        }

        function hideTyping() {
            const el = document.getElementById("glab-typing-indicator");
            if (el) el.remove();
        }

        function setSending(isSending) {
            input.disabled = isSending;
            if (sendBtn) sendBtn.disabled = isSending;
        }

        function togglePanel(open) {
            const shouldOpen = open !== undefined ? open : !panel.classList.contains("open");
            panel.classList.toggle("open", shouldOpen);
            if (shouldOpen && !messages.dataset.greeted) {
                appendMessage(
                    "Hi! I'm the GeniuzLab assistant. Ask me about hiring a creative, courses, wallet, or anything else on the site.",
                    "bot"
                );
                messages.dataset.greeted = "1";
                input.focus();
            }
        }

        function sendMessage(text) {
            if (!text) return;
            appendMessage(text, "user");
            setSending(true);
            showTyping();

            const controller = new AbortController();
            const timeout = setTimeout(function () { controller.abort(); }, 15000);

            fetch(window.GLAB_ASSISTANT_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ message: text }),
                signal: controller.signal,
            })
                .then(function (r) {
                    const contentType = r.headers.get("content-type") || "";
                    if (!r.ok || contentType.indexOf("application/json") === -1) {
                        // The request reached the server but didn't get a
                        // usable JSON reply back (CSRF rejection, a 500,
                        // an auth redirect, etc). Treat this as a server
                        // error rather than letting r.json() throw a
                        // confusing parse error further down the chain.
                        throw new Error("assistant_bad_response");
                    }
                    return r.json();
                })
                .then(function (data) {
                    hideTyping();
                    const bubble = appendMessage(
                        data && data.reply ? data.reply : "Sorry, I didn't quite get that — could you rephrase it?",
                        "bot"
                    );
                    if (data && data.escalate && bubble) bubble.classList.add("glab-msg-escalate");
                    if (data && data.redirect_url) {
                        handleRedirect(data.redirect_url);
                    } else if (data) {
                        appendQuickReplies(data.quick_replies);
                        appendLinks(data.links);
                    }
                })
                .catch(function (err) {
                    hideTyping();
                    const message = err && err.name === "AbortError"
                        ? "That's taking longer than expected — please try again in a moment."
                        : "Sorry, I couldn't reach the server just now — please try again in a moment.";
                    appendMessage(message, "bot");
                })
                .finally(function () {
                    clearTimeout(timeout);
                    setSending(false);
                    input.focus();
                });
        }

        launcher.addEventListener("click", function () { togglePanel(); });
        if (closeBtn) closeBtn.addEventListener("click", function () { togglePanel(false); });

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;
            input.value = "";
            sendMessage(text);
        });
    });
})();
