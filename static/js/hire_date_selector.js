// Hire Date Selector JavaScript
$(document).ready(function() {
    console.log('Hire date selector ready');

    // Load saved dates on page load
    fetch('/api/hire-dates/')
        .then(function(resp) { return resp.json(); })
        .then(function(data) {
            console.log('Loaded dates:', data);
            updateNavbarDisplay(data.start_date, data.end_date);
        })
        .catch(function(e) { console.log('Error:', e); });

    // Set min date to today
    var today = new Date().toISOString().split('T')[0];
    var startInput = document.getElementById('hireStartDate');
    var endInput = document.getElementById('hireEndDate');
    if (startInput) startInput.setAttribute('min', today);
    if (endInput) endInput.setAttribute('min', today);

    // Listen for date changes
    if (startInput) {
        startInput.addEventListener('change', function() {
            if (endInput && this.value && endInput.value && new Date(endInput.value) < new Date(this.value)) {
                endInput.value = this.value;
            }
            if (endInput) endInput.setAttribute('min', this.value);
            updateDateSummary();
        });
    }
    if (endInput) {
        endInput.addEventListener('change', updateDateSummary);
    }

    function updateNavbarDisplay(start, end) {
        var display = document.getElementById('selectedDatesDisplay');
        if (display && start && end) {
            var s = new Date(start).toLocaleDateString('en-AU', {day: 'numeric', month: 'short'});
            var e = new Date(end).toLocaleDateString('en-AU', {day: 'numeric', month: 'short'});
            display.textContent = s + ' - ' + e;
            console.log('Display set to:', display.textContent);
        } else if (display) {
            display.textContent = 'Select Dates';
            console.log('Display cleared');
        }
    }

    function updateDateSummary() {
        var startInput = document.getElementById('hireStartDate');
        var endInput = document.getElementById('hireEndDate');
        var summary = document.getElementById('hireDateSummary');
        var periodText = document.getElementById('hirePeriodText');
        
        if (startInput && endInput && startInput.value && endInput.value) {
            var start = new Date(startInput.value);
            var end = new Date(endInput.value);
            var days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
            
            if (periodText) periodText.textContent = startInput.value + ' to ' + endInput.value + ' (' + days + ' days)';
            if (summary) summary.classList.remove('d-none');
        }
    }

    // Confirm button
    var confirmBtn = document.getElementById('confirmHireDates');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            var startInput = document.getElementById('hireStartDate');
            var endInput = document.getElementById('hireEndDate');
            
            if (startInput && endInput && startInput.value && endInput.value) {
                fetch('/api/hire-dates/set/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        start_date: startInput.value,
                        end_date: endInput.value
                    })
                })
                .then(function(resp) { return resp.json(); })
                .then(function(data) {
                    updateNavbarDisplay(startInput.value, endInput.value);
                    $('#hireDateModal').modal('hide');
                });
            }
        });
    }

    // Clear button
    var clearBtn = document.getElementById('clearHireDates');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            fetch('/api/hire-dates/clear/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCSRFToken() }
            })
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                updateNavbarDisplay(null, null);
                var startInput = document.getElementById('hireStartDate');
                var endInput = document.getElementById('hireEndDate');
                if (startInput) startInput.value = '';
                if (endInput) endInput.value = '';
                var summary = document.getElementById('hireDateSummary');
                if (summary) summary.classList.add('d-none');
                $('#hireDateModal').modal('hide');
            });
        });
    }

    // Add to Basket validation
    var addToBasketForm = document.getElementById('add_to_basket_form');
    if (addToBasketForm) {
        addToBasketForm.addEventListener('submit', function(e) {
            // Prevent default immediately
            e.preventDefault();
            e.stopPropagation();
            
            var btn = this.querySelector('button[type="submit"]');
            
            fetch('/api/hire-dates/')
                .then(function(resp) { return resp.json(); })
                .then(function(data) {
                    if (!data.start_date || !data.end_date) {
                        alert('Please select hire dates first using the "Select Dates" button in the navbar.');
                        $('#hireDateModal').modal('show');
                        // Re-enable button if it was disabled
                        if (btn) {
                            btn.disabled = false;
                            btn.removeAttribute('data-loading-text');
                            btn.textContent = 'Add to basket';
                        }
                        return false;
                    }
                    // Dates selected - submit the form manually
                    e.target.submit();
                })
                .catch(function(e) { 
                    // On error, allow submission
                    e.target.submit();
                });
            
            return false;
        });
    }

    function getCSRFToken() {
        var name = 'csrftoken';
        var cookieValue = null;
        if (document.cookie) {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});