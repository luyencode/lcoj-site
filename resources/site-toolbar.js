$(document).ready(function() {
    var $toolbar = $('#site-toolbar');
    var $toolbarToggle = $('#site-toolbar-toggle');
    var $toolbarToggleIcon = $toolbarToggle.find('.fa');
    var $toolbarPanel = $('#site-toolbar-panel');
    var $donateModal = $('#donate-modal');
    var $donateTriggers = $('.js-open-donate');
    var hoverCloseTimer = null;

    function openDonateModal() {
        $donateModal.addClass('show');
        $('body').css('overflow', 'hidden');
    }

    function closeDonateModal() {
        $donateModal.removeClass('show');
        $('body').css('overflow', '');
    }

    function closeToolbar() {
        $toolbar.removeClass('is-open');
        $toolbar.removeClass('is-hovered');
        $toolbarToggle.attr('aria-expanded', 'false');
        $toolbarToggleIcon.removeClass('fa-angle-double-right').addClass('fa-angle-double-left');
    }

    function setToolbarHovered(isHovered) {
        if (hoverCloseTimer) {
            clearTimeout(hoverCloseTimer);
            hoverCloseTimer = null;
        }

        if (isHovered) {
            $toolbar.addClass('is-hovered');
            return;
        }

        if ($toolbar.hasClass('is-open')) {
            return;
        }

        hoverCloseTimer = setTimeout(function() {
            $toolbar.removeClass('is-hovered');
        }, 70);
    }

    function toggleToolbar() {
        var isOpen = $toolbar.hasClass('is-open');

        $toolbar.toggleClass('is-open', !isOpen);
        $toolbar.toggleClass('is-hovered', !isOpen);
        $toolbarToggle.attr('aria-expanded', String(!isOpen));
        $toolbarToggleIcon
            .toggleClass('fa-angle-double-left', isOpen)
            .toggleClass('fa-angle-double-right', !isOpen);
    }

    $toolbarToggle.on('mouseenter', function() {
        setToolbarHovered(true);
    });

    $toolbarPanel.on('mouseenter', function() {
        setToolbarHovered(true);
    });

    $toolbarToggle.on('mouseleave', function() {
        setToolbarHovered(false);
    });

    $toolbarPanel.on('mouseleave', function() {
        setToolbarHovered(false);
    });

    $toolbarToggle.on('click', function(e) {
        e.preventDefault();
        toggleToolbar();
    });

    $donateTriggers.on('click', function(e) {
        e.preventDefault();
        openDonateModal();
    });

    $donateModal.on('click', function(e) {
        if (e.target === this) {
            closeDonateModal();
        }
    });

    $(document).on('click', function(e) {
        if (!$toolbar.length || !$toolbar.hasClass('is-open')) {
            return;
        }

        if ($(e.target).closest('#site-toolbar').length === 0) {
            closeToolbar();
        }
    });

    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') {
            if ($donateModal.hasClass('show')) {
                closeDonateModal();
            }

            closeToolbar();
        }
    });
});
