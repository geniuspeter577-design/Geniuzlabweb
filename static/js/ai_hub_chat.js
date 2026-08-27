(function () {
    "use strict";

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    // ---- Minimal, self-contained Markdown renderer -------------------
    // Escapes all HTML first, then layers Markdown syntax on top, so
    // nothing the model (or a user's own past message) contains can
    // inject markup. Deliberately dependency-free — the assistant's
    // formatting needs (headers, bold/italic, links, lists, fenced code
    // with a language tag, inline code) are a fixed, small set.
    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderInline(text) {
        let out = escapeHtml(text);
        out = out.replace(/`([^`]+)`/g, '<code class="aihub-inline-code">$1</code>');
        out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        return out;
    }

    function renderMarkdown(raw) {
        const lines = (raw || "").replace(/\r\n/g, "\n").split("\n");
        let html = "";
        let i = 0;
        let listBuffer = [];
        let listType = null;

        function flushList() {
            if (listBuffer.length) {
                const tag = listType === "ol" ? "ol" : "ul";
                html += `<${tag}>` + listBuffer.map((li) => `<li>${renderInline(li)}</li>`).join("") + `</${tag}>`;
                listBuffer = [];
                listType = null;
            }
        }

        while (i < lines.length) {
            const line = lines[i];

            // Fenced code block
            const fenceMatch = line.match(/^```(\w*)\s*$/);
            if (fenceMatch) {
                flushList();
                const lang = fenceMatch[1] || "text";
                const codeLines = [];
                i++;
                while (i < lines.length && !/^```\s*$/.test(lines[i])) {
                    codeLines.push(lines[i]);
                    i++;
                }
                i++; // skip closing fence
                const codeText = codeLines.join("\n");
                const escaped = escapeHtml(codeText);
                html +=
                    '<div class="aihub-code-block">' +
                    `<div class="aihub-code-head"><span>${escapeHtml(lang)}</span>` +
                    '<button type="button" class="aihub-code-copy" data-code="' + encodeURIComponent(codeText) + '">Copy</button></div>' +
                    `<pre><code>${escaped}</code></pre></div>`;
                continue;
            }

            // Headers
            const headerMatch = line.match(/^(#{1,3})\s+(.*)$/);
            if (headerMatch) {
                flushList();
                const level = headerMatch[1].length + 3; // h4..h6, keeps chat bubbles from looking like page titles
                html += `<h${level}>${renderInline(headerMatch[2])}</h${level}>`;
                i++;
                continue;
            }

            // Unordered list item
            const ulMatch = line.match(/^\s*[-*]\s+(.*)$/);
            if (ulMatch) {
                if (listType && listType !== "ul") flushList();
                listType = "ul";
                listBuffer.push(ulMatch[1]);
                i++;
                continue;
            }

            // Ordered list item
            const olMatch = line.match(/^\s*\d+\.\s+(.*)$/);
            if (olMatch) {
                if (listType && listType !== "ol") flushList();
                listType = "ol";
                listBuffer.push(olMatch[1]);
                i++;
                continue;
            }

            flushList();

            if (line.trim() === "") {
                i++;
                continue;
            }

            html += `<p>${renderInline(line)}</p>`;
            i++;
        }
        flushList();
        return html;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const sidebar = document.getElementById("aihub-sidebar");
        const sidebarToggle = document.getElementById("aihub-sidebar-toggle");
        if (sidebar && sidebarToggle) {
            sidebarToggle.addEventListener("click", function (e) {
                e.stopPropagation();
                sidebar.classList.toggle("open");
            });
            document.addEventListener("click", function (e) {
                if (!sidebar.classList.contains("open")) return;
                if (sidebar.contains(e.target) || e.target === sidebarToggle) return;
                sidebar.classList.remove("open");
            });
        }

        const chatWindow = document.getElementById("aihub-chat-window");
        const form = document.getElementById("aihub-chat-form");
        if (!chatWindow) return;

        // Render any messages that were already in the thread on page load.
        chatWindow.querySelectorAll(".aihub-chat-bubble").forEach(function (bubble) {
            const msgEl = bubble.closest(".aihub-chat-msg");
            const raw = msgEl ? msgEl.getAttribute("data-raw") : "";
            bubble.innerHTML = renderMarkdown(raw || "");
        });
        scrollToBottom();

        chatWindow.addEventListener("click", function (e) {
            const btn = e.target.closest(".aihub-code-copy");
            if (!btn) return;
            const code = decodeURIComponent(btn.getAttribute("data-code") || "");
            navigator.clipboard.writeText(code).then(function () {
                const original = btn.textContent;
                btn.textContent = "Copied!";
                setTimeout(function () { btn.textContent = original; }, 1500);
            });
        });

        function scrollToBottom() {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        function addMessage(role, initialText) {
            const emptyState = chatWindow.querySelector(".aihub-chat-empty");
            if (emptyState) emptyState.remove();

            const wrap = document.createElement("div");
            wrap.className = "aihub-chat-msg aihub-chat-msg-" + role;

            const avatar = document.createElement("div");
            avatar.className = "aihub-chat-avatar";
            avatar.innerHTML = role === "assistant" ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';

            const bubble = document.createElement("div");
            bubble.className = "aihub-chat-bubble";
            bubble.dataset.role = role;
            bubble.textContent = initialText || "";

            wrap.appendChild(avatar);
            wrap.appendChild(bubble);
            chatWindow.appendChild(wrap);
            scrollToBottom();
            return bubble;
        }

        if (!form) return;

        const input = document.getElementById("aihub-chat-input");
        const sendBtn = document.getElementById("aihub-chat-send");

        input.addEventListener("input", function () {
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 160) + "px";
        });

        input.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                form.requestSubmit();
            }
        });

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            addMessage("user", text).innerHTML = renderMarkdown(text);
            input.value = "";
            input.style.height = "auto";
            input.disabled = true;
            sendBtn.disabled = true;

            const assistantBubble = addMessage("assistant", "");
            assistantBubble.classList.add("aihub-chat-typing");
            let raw = "";

            fetch(window.GLAB_CHAT_SEND_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ message: text }),
            })
                .then(function (response) {
                    if (!response.ok || !response.body) {
                        throw new Error("bad-response");
                    }
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = "";

                    function pump() {
                        return reader.read().then(function (result) {
                            if (result.done) return;
                            buffer += decoder.decode(result.value, { stream: true });

                            const events = buffer.split("\n\n");
                            buffer = events.pop(); // last chunk may be incomplete

                            events.forEach(function (evt) {
                                const line = evt.trim();
                                if (!line.startsWith("data:")) return;
                                let payload;
                                try {
                                    payload = JSON.parse(line.slice(5).trim());
                                } catch (err) {
                                    return;
                                }
                                if (payload.chunk) {
                                    raw += payload.chunk;
                                    assistantBubble.classList.remove("aihub-chat-typing");
                                    assistantBubble.innerHTML = renderMarkdown(raw);
                                    scrollToBottom();
                                } else if (payload.error) {
                                    assistantBubble.classList.remove("aihub-chat-typing");
                                    assistantBubble.innerHTML = renderMarkdown(payload.error);
                                    assistantBubble.classList.add("aihub-chat-error");
                                } else if (payload.done) {
                                    assistantBubble.classList.remove("aihub-chat-typing");
                                }
                            });

                            return pump();
                        });
                    }
                    return pump();
                })
                .catch(function () {
                    assistantBubble.classList.remove("aihub-chat-typing");
                    assistantBubble.classList.add("aihub-chat-error");
                    assistantBubble.innerHTML = renderMarkdown("Couldn't reach the server — please try again.");
                })
                .finally(function () {
                    input.disabled = false;
                    sendBtn.disabled = false;
                    input.focus();
                });
        });
    });
})();
