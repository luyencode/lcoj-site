(function () {
    'use strict';

    var MOBILE_BREAKPOINT = 600;
    var RENDER_SCALE_CAP = 2;
    var BOTTOM_MARGIN = 24;
    var MIN_FIT_HEIGHT = 350; // matches .flipbook-container's CSS min-height floor
    var FULLSCREEN_MARGIN = 48;
    var ZOOM_MIN = 1;
    var ZOOM_MAX = 2.5;
    var ZOOM_STEP = 0.25;

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

    // Only the navbar is fixed chrome that permanently eats into the viewport.
    // The footer and any content above the flipbook (hero/back-link) are
    // normal scrollable flow — the user can scroll the flipbook into view, so
    // they're not subtracted here; doing so would needlessly shrink the book.
    function getNavbarHeight() {
        var navbar = document.getElementById('navigation') || document.querySelector('nav');
        return navbar ? navbar.getBoundingClientRect().height : 56;
    }

    function computeAvailableHeight() {
        var available = window.innerHeight - getNavbarHeight() - BOTTOM_MARGIN;
        return Math.max(MIN_FIT_HEIGHT, available);
    }

    function computeFullscreenHeight() {
        return Math.max(MIN_FIT_HEIGHT, window.innerHeight - FULLSCREEN_MARGIN);
    }

    function isFullscreenElement(el) {
        return document.fullscreenElement === el || document.webkitFullscreenElement === el;
    }

    function requestFullscreen(el) {
        var request = el.requestFullscreen || el.webkitRequestFullscreen;
        if (request) {
            request.call(el);
        }
    }

    function exitFullscreen() {
        var exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) {
            exit.call(document);
        }
    }

    function buildToolbar(wrapper, api) {
        var toolbar = document.createElement('div');
        toolbar.className = 'flipbook-toolbar';

        function makeButton(iconClass, title, onClick) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'flipbook-toolbar-btn';
            btn.title = title;
            btn.setAttribute('aria-label', title);
            var icon = document.createElement('i');
            icon.className = 'fa ' + iconClass;
            btn.appendChild(icon);
            btn.addEventListener('click', onClick);
            return {button: btn, icon: icon};
        }

        var zoomOut = makeButton('fa-search-minus', gettext('Zoom out'), function () {
            api.zoomOut();
        });
        var zoomIn = makeButton('fa-search-plus', gettext('Zoom in'), function () {
            api.zoomIn();
        });
        toolbar.appendChild(zoomOut.button);
        toolbar.appendChild(zoomIn.button);

        var sound = null;
        if (api.hasSound()) {
            sound = makeButton(api.isMuted() ? 'fa-volume-off' : 'fa-volume-up', gettext('Toggle sound'), function () {
                var muted = api.toggleSound();
                sound.icon.className = 'fa ' + (muted ? 'fa-volume-off' : 'fa-volume-up');
            });
            toolbar.appendChild(sound.button);
        }

        var fullscreen = makeButton('fa-expand', gettext('Fullscreen'), function () {
            api.toggleFullscreen();
        });
        toolbar.appendChild(fullscreen.button);

        wrapper.appendChild(toolbar);

        return {
            updateZoomButtons: function (zoomLevel) {
                zoomOut.button.disabled = zoomLevel <= ZOOM_MIN;
                zoomIn.button.disabled = zoomLevel >= ZOOM_MAX;
            },
            updateFullscreenIcon: function (isFullscreen) {
                fullscreen.icon.className = 'fa ' + (isFullscreen ? 'fa-compress' : 'fa-expand');
            },
        };
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

        var wrapper = container.closest('.flipbook-wrapper') || container.parentNode;
        var targetWidth = container.clientWidth || 600;

        // "Turning a page.ogg" by planish (via PDSounds.org), public domain,
        // https://commons.wikimedia.org/wiki/File:Turning_a_page.ogg
        var flipSoundUrl = container.getAttribute('data-flip-sound-url');
        var flipSound = null;
        if (flipSoundUrl) {
            flipSound = new Audio(flipSoundUrl);
            flipSound.preload = 'auto';
            flipSound.volume = 0.5;
            flipSound.muted = localStorage.getItem('flipbook-muted') === '1';
        }
        // loadFromImages/updateFromImages re-render the current spread and,
        // as a side effect, fire the library's 'flip' event even though no
        // page actually turned (initial load, and once per page while we
        // progressively swap in rendered images below) — suppress the sound
        // during those synchronous calls so it only plays on real page turns.
        var suppressFlipSound = false;

        var pageFlip = null;
        var images = null;
        var aspectRatio = 1;
        var zoomLevel = ZOOM_MIN;
        var toolbarUi = null;
        var currentFitWidth = 0;

        function updateSinglePageState() {
            // showCover:true renders the first/last page alone in desktop double-page
            // ("landscape") mode, but StPageFlip still draws a full two-page-spread
            // canvas and positions that lone page flush to the outer edge (mimicking a
            // physical book's front/back cover) — the other half of the canvas is
            // blank. There's no library option for this, so it's fixed here: clip the
            // wrapper down to one page's width and shift the spread so the drawn half
            // lands centered instead of flush to one side.
            var isSingle = false;
            var isFrontCover = false;
            if (pageFlip && pageFlip.getOrientation() === 'landscape') {
                var index = pageFlip.getCurrentPageIndex();
                isSingle = index === 0 || index === pageFlip.getPageCount() - 1;
                isFrontCover = index === 0;
            }
            // Fullscreen already flex-centers the (still full-spread-width) container
            // itself via CSS; narrowing the wrapper's own `width` there would fight the
            // browser's `:fullscreen` sizing, so this framing is only applied outside
            // fullscreen.
            var applyFrame = isSingle && !isFullscreenElement(wrapper);
            wrapper.classList.toggle('flipbook-wrapper--single-page', applyFrame);
            if (applyFrame) {
                // .flipbook-container's own CSS width is `100%` of this wrapper, and
                // StPageFlip's `size: 'stretch'` reacts to the container's own measured
                // box — so narrowing the wrapper alone would make the library think its
                // available space shrank and redraw the whole spread smaller. Pin the
                // container to its full (still two-page) spread width explicitly first,
                // so only the wrapper's overflow clips it, nothing gets redrawn.
                container.style.width = (currentFitWidth * 2) + 'px';
                wrapper.style.width = currentFitWidth + 'px';
                container.style.marginLeft = isFrontCover ? (-currentFitWidth) + 'px' : '0';
            } else {
                container.style.width = '';
                wrapper.style.width = '';
                container.style.marginLeft = '';
            }
        }

        function buildPageFlip(fitWidth, imagesToLoad) {
            var isMobile = fitWidth < MOBILE_BREAKPOINT;
            currentFitWidth = fitWidth;
            container.innerHTML = '';
            var instance = new window.St.PageFlip(container, Object.assign({
                width: fitWidth,
                height: Math.round(fitWidth * aspectRatio),
                size: 'stretch',
                minWidth: 250,
                maxWidth: fitWidth,
                minHeight: Math.round(250 * aspectRatio),
                maxHeight: Math.round(fitWidth * aspectRatio),
                usePortrait: isMobile,
                showCover: true,
                // Default is 1000ms; shortened so the flip sound (which fires on
                // completion, since StPageFlip has no reliable "flip started" event
                // for drag-released turns) doesn't lag too far behind the click/release.
                flippingTime: 600,
            }, options));

            instance.on('flip', function () {
                if (!suppressFlipSound && flipSound) {
                    flipSound.currentTime = 0;
                    flipSound.play().catch(function () {});
                }
                updateSinglePageState();
            });

            suppressFlipSound = true;
            instance.loadFromImages(imagesToLoad);
            suppressFlipSound = false;
            // `size: 'stretch'` makes StPageFlip track its own container size on
            // window resize internally, but `maxWidth`/`maxHeight` above are pinned to
            // the viewport-fit size computed at (re)build time, so it can never grow
            // past what's actually visible on screen without a rebuild (see
            // rebuildAtFit, called only on fullscreen enter/exit).
            return instance;
        }

        function currentAvailableHeight() {
            return isFullscreenElement(wrapper) ? computeFullscreenHeight() : computeAvailableHeight();
        }

        function applyZoom() {
            container.style.transform = zoomLevel === ZOOM_MIN ? '' : 'scale(' + zoomLevel + ')';
            if (zoomLevel > ZOOM_MIN) {
                wrapper.style.maxHeight = currentAvailableHeight() + 'px';
            } else {
                wrapper.style.maxHeight = '';
            }
            wrapper.classList.toggle('flipbook-wrapper--zoomed', zoomLevel > ZOOM_MIN);
        }

        function rebuildAtFit() {
            if (!images) {
                return;
            }
            var fitWidth = Math.min(container.clientWidth || targetWidth, Math.round(currentAvailableHeight() / aspectRatio));
            pageFlip = buildPageFlip(fitWidth, images);
            applyZoom();
            updateSinglePageState();
        }

        var api = {
            zoomIn: function () {
                zoomLevel = Math.min(ZOOM_MAX, Math.round((zoomLevel + ZOOM_STEP) * 100) / 100);
                applyZoom();
                toolbarUi.updateZoomButtons(zoomLevel);
            },
            zoomOut: function () {
                zoomLevel = Math.max(ZOOM_MIN, Math.round((zoomLevel - ZOOM_STEP) * 100) / 100);
                applyZoom();
                toolbarUi.updateZoomButtons(zoomLevel);
            },
            hasSound: function () {
                return !!flipSound;
            },
            isMuted: function () {
                return !!flipSound && flipSound.muted;
            },
            toggleSound: function () {
                if (!flipSound) {
                    return false;
                }
                flipSound.muted = !flipSound.muted;
                localStorage.setItem('flipbook-muted', flipSound.muted ? '1' : '0');
                return flipSound.muted;
            },
            toggleFullscreen: function () {
                if (isFullscreenElement(wrapper)) {
                    exitFullscreen();
                } else {
                    requestFullscreen(wrapper);
                }
            },
        };

        function onFullscreenChange() {
            var isFullscreen = isFullscreenElement(wrapper);
            wrapper.classList.toggle('flipbook-wrapper--fullscreen', isFullscreen);
            if (toolbarUi) {
                toolbarUi.updateFullscreenIcon(isFullscreen);
            }
            rebuildAtFit();
        }
        document.addEventListener('fullscreenchange', onFullscreenChange);
        document.addEventListener('webkitfullscreenchange', onFullscreenChange);

        // pdf.js v6 dropped the bare-string shorthand: the source must be an
        // options object ({url: ...}) for `url`/`data`/`range` to be recognized.
        window.pdfjsLib.getDocument({url: pdfUrl}).promise.then(function (pdfDocument) {
            var numPages = pdfDocument.numPages;

            return pdfDocument.getPage(1).then(function (firstPage) {
                var baseViewport = firstPage.getViewport({scale: 1});
                aspectRatio = baseViewport.height / baseViewport.width;

                var fitWidth = Math.min(targetWidth, Math.round(computeAvailableHeight() / aspectRatio));

                return renderCanvasImage(firstPage, fitWidth).then(function (firstImage) {
                    images = new Array(numPages).fill(firstImage);
                    pageFlip = buildPageFlip(fitWidth, images);
                    toolbarUi = buildToolbar(wrapper, api);
                    updateSinglePageState();

                    var pending = Promise.resolve();
                    for (var n = 2; n <= numPages; n++) {
                        (function (pageNumber) {
                            pending = pending.then(function () {
                                return renderPageToImage(pdfDocument, pageNumber, fitWidth).then(function (image) {
                                    images[pageNumber - 1] = image;
                                    suppressFlipSound = true;
                                    pageFlip.updateFromImages(images);
                                    suppressFlipSound = false;
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
