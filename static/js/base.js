/* ── Navbar scroll ───────────────────────────────────────── */
(function() {
    const nav    = document.getElementById('rcyber-nav');
    const isHero = nav.classList.contains('transparent');

    /* Pages sans hero (solid/light) : rien à faire, la nav est déjà opaque */
    if (!isHero) return;

    /* Pages avec hero : transparent → scrolled quand on descend */
    function update() {
        if (window.scrollY > 60) {
            nav.classList.remove('transparent');
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
            nav.classList.add('transparent');
        }
    }
    window.addEventListener('scroll', update, { passive: true });
    update();
})();

/* ── Drawer ──────────────────────────────────────────────── */
function openDrawer() {
    document.getElementById('drawer-panel').classList.add('open');
    document.getElementById('drawer-overlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeDrawer() {
    document.getElementById('drawer-panel').classList.remove('open');
    document.getElementById('drawer-overlay').classList.remove('open');
    document.body.style.overflow = '';
}
function toggleDrawerServices(btn) {
    const list = document.getElementById('drawer-services');
    btn.classList.toggle('open');
    list.classList.toggle('open');
}

/* ── Search ──────────────────────────────────────────────── */
function openSearch() {
    document.getElementById('search-overlay').classList.add('open');
    setTimeout(() => document.getElementById('search-input').focus(), 50);
    document.body.style.overflow = 'hidden';
}
function closeSearch() {
    document.getElementById('search-overlay').classList.remove('open');
    document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openSearch(); }
    if (e.key === 'Escape') { closeSearch(); closeDrawer(); }
});