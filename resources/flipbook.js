(function () {
    'use strict';

    var MOBILE_BREAKPOINT = 600;
    var RENDER_SCALE_CAP = 2;

    function renderCanvasImage(page, targetWidth) {
        var baseViewport = page.getViewport({scale: 1});
        var scale = Math.min(RENDER_SCALE_CAP, (targetWidth / baseViewport.width) * (window.devicePixelRatio || 1));
        var viewport = page.getViewport({scale: scale});

        var canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        return page.render({canvasContext: canvas.getContext('2d'), viewport: viewport}).promise.then(function () {
            return canvas.toDataURL('image/jpeg', 0.85);
        });
    }

    function renderPageToImage(pdfDocument, pageNumber, targetWidth) {
        return pdfDocument.getPage(pageNumber).then(function (page) {
            return renderCanvasImage(page, targetWidth);
        });
    }

    function showFallback(container, pdfUrl, message) {
        container.innerHTML = '';
        var link = document.createElement('a');
        link.href = pdfUrl;
        link.className = 'flipbook-fallback-link';
        link.textContent = message;
        container.appendChild(link);
    }

    function showLoading(container) {
        container.innerHTML = '<div class="flipbook-loading">' + gettext('Loading document…') + '</div>';
    }

    function gettext(s) {
        return (window.gettext || function (x) { return x; })(s);
    }

    // pdfjs-init.js loads as a deferred `type="module"` script, so it can finish
    // after this (classic, non-deferred) script has already run — wait for its
    // ready signal instead of assuming load order.
    function whenPdfJsReady(callback) {
        if (window.pdfjsLib) {
            callback();
            return;
        }
        var timer = setTimeout(function () {
            window.removeEventListener('pdfjslib:ready', onReady);
            callback();
        }, 8000);
        function onReady() {
            clearTimeout(timer);
            callback();
        }
        window.addEventListener('pdfjslib:ready', onReady, {once: true});
    }

    function initFlipbook(containerId, pdfUrl, options) {
        var container = document.getElementById(containerId);
        if (!container || !pdfUrl) {
            return;
        }
        showLoading(container);
        whenPdfJsReady(function () {
            doInitFlipbook(container, pdfUrl, options);
        });
    }

    function doInitFlipbook(container, pdfUrl, options) {
        if (!window.pdfjsLib || !window.St || !window.St.PageFlip) {
            showFallback(container, pdfUrl, gettext('Download PDF'));
            return;
        }

        options = options || {};

        var targetWidth = container.clientWidth || 600;
        var isMobile = targetWidth < MOBILE_BREAKPOINT;

        // pdf.js v6 dropped the bare-string shorthand: the source must be an
        // options object ({url: ...}) for `url`/`data`/`range` to be recognized.
        window.pdfjsLib.getDocument({url: pdfUrl}).promise.then(function (pdfDocument) {
            var numPages = pdfDocument.numPages;

            return pdfDocument.getPage(1).then(function (firstPage) {
                var baseViewport = firstPage.getViewport({scale: 1});
                var aspectRatio = baseViewport.height / baseViewport.width;

                return renderCanvasImage(firstPage, targetWidth).then(function (firstImage) {
                    container.innerHTML = '';
                    var pageFlip = new window.St.PageFlip(container, Object.assign({
                        width: targetWidth,
                        height: Math.round(targetWidth * aspectRatio),
                        size: 'stretch',
                        minWidth: 250,
                        maxWidth: 1400,
                        minHeight: Math.round(250 * aspectRatio),
                        maxHeight: Math.round(1400 * aspectRatio),
                        usePortrait: isMobile,
                        showCover: true,
                    }, options));

                    var images = new Array(numPages).fill(firstImage);
                    pageFlip.loadFromImages(images);
                    // `size: 'stretch'` makes StPageFlip track its own container size on
                    // window resize internally — no manual resize handling needed here.

                    var pending = Promise.resolve();
                    for (var n = 2; n <= numPages; n++) {
                        (function (pageNumber) {
                            pending = pending.then(function () {
                                return renderPageToImage(pdfDocument, pageNumber, targetWidth).then(function (image) {
                                    images[pageNumber - 1] = image;
                                    pageFlip.updateFromImages(images);
                                });
                            });
                        })(n);
                    }
                    return pending;
                });
            });
        }).catch(function (err) {
            console.error('[flipbook] failed to load ' + pdfUrl, err);
            showFallback(container, pdfUrl, gettext('Could not load preview — download PDF'));
        });
    }

    function autoInit() {
        var containers = document.querySelectorAll('.flipbook-container[data-pdf-url]');
        if (!containers.length) {
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    observer.unobserve(entry.target);
                    initFlipbook(entry.target.id, entry.target.getAttribute('data-pdf-url'));
                }
            });
        }, {rootMargin: '200px'});

        containers.forEach(function (el) {
            observer.observe(el);
        });
    }

    window.initFlipbook = initFlipbook;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }
})();
