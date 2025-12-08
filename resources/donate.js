// Donate Button and Modal Functionality
$(document).ready(function() {
    var $donateButton = $('#donate-button');
    var $donateModal = $('#donate-modal');
    
    // Open modal when button is clicked
    $donateButton.on('click', function() {
        $donateModal.addClass('show');
        $('body').css('overflow', 'hidden'); // Prevent background scrolling
    });
    
    // Close modal when clicking outside the modal content
    $donateModal.on('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    // Close modal when pressing ESC key
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $donateModal.hasClass('show')) {
            closeModal();
        }
    });
    
    function closeModal() {
        $donateModal.removeClass('show');
        $('body').css('overflow', ''); // Restore scrolling
    }
});
