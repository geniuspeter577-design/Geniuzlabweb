// Disables the submit button on any form marked `data-guard-submit` the
// moment it's submitted, so a double-click or a slow connection can't fire
// the same POST twice (wallet debits, subscriptions, VTU purchases).
// The disabled state only exists in the browser's current DOM — if the
// server re-renders the page after a validation error, the button comes
// back enabled automatically on the fresh page load. No effect on forms
// that don't opt in via the attribute.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-guard-submit]').forEach(function (form) {
        form.addEventListener('submit', function () {
            var btn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (!btn || btn.disabled) return;
            btn.disabled = true;
            btn.dataset.originalText = btn.dataset.originalText || btn.textContent;
            btn.textContent = 'Please wait…';
        });
    });
});
