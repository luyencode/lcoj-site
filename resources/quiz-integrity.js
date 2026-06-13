/* Quiz integrity monitoring — runs only when window.quizIntegrityConfig is set. */
(function () {
    'use strict';

    var cfg = window.quizIntegrityConfig;
    if (!cfg) return;

    var DEBOUNCE_MS = 5000;
    var lastFired = {};

    function canFire(type) {
        var now = Date.now();
        if (lastFired[type] && now - lastFired[type] < DEBOUNCE_MS) return false;
        lastFired[type] = now;
        return true;
    }

    var toastEl = document.getElementById('quiz-integrity-toast');
    var toastTimer = null;

    function showToast(msg) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.style.display = 'block';
        if (toastTimer) clearTimeout(toastTimer);
        toastTimer = setTimeout(function () {
            toastEl.style.display = 'none';
        }, 4000);
    }

    function record(type, msg) {
        if (!canFire(type)) return;
        showToast(msg);
        fetch(cfg.violationUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': cfg.csrfToken,
            },
            body: JSON.stringify({
                type: type,
                occurred_at: new Date().toISOString(),
                extra_data: {},
            }),
        }).catch(function () {});
    }

    /* Suppress false positives during quiz submission / page navigation */
    var submitting = false;
    window.addEventListener('beforeunload', function () { submitting = true; });
    document.addEventListener('submit', function () {
        submitting = true;
        setTimeout(function () { submitting = false; }, 1000);
    }, true);

    /* Tab switch */
    document.addEventListener('visibilitychange', function () {
        if (document.hidden && !submitting) {
            record('tab_switch', '⚠ Tab switch detected. This has been recorded.');
        }
    });

    /* Window blur */
    window.addEventListener('blur', function () {
        if (submitting || window.quizConfirmOpen) return;
        record('window_blur', '⚠ Window blur detected. This has been recorded.');
    });

    /* PrintScreen key */
    document.addEventListener('keydown', function (e) {
        if (e.key === 'PrintScreen') {
            record('print_screen', '⚠ Screenshot key detected. This has been recorded.');
        }
    });

    /* Copy block */
    document.addEventListener('copy', function (e) {
        e.preventDefault();
        record('copy_attempt', '⚠ Copying is not allowed during this quiz.');
    });

    /* Right-click disable (part of copy enforcement) */
    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
    });

    /* DevTools detection — periodic window size heuristic */
    var devtoolsOpen = false;
    setInterval(function () {
        var widthDelta = window.outerWidth - window.innerWidth;
        var heightDelta = window.outerHeight - window.innerHeight;
        var detected = widthDelta > 160 || heightDelta > 160;
        if (detected && !devtoolsOpen) {
            devtoolsOpen = true;
            record('devtools', '⚠ DevTools detected. This has been recorded.');
        } else if (!detected) {
            devtoolsOpen = false;
        }
    }, 1000);

}());
