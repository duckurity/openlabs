// VaultCorp — global UI helpers
document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 s
    document.querySelectorAll('.alert').forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity .4s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 400);
        }, 5000);
    });
});
