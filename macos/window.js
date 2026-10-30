// macOS shell only: the Windows page retains its original double-click binding.
(function () {
    const avatar = document.querySelector('.nav-avatar');
    if (!avatar || avatar.dataset.macosControls === '1') return;
    avatar.dataset.macosControls = '1';
    avatar.title = '单击最小化 | 右键退出';
    avatar.addEventListener('click', function () {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.minimize();
        }
    });
})();
