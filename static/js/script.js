document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flash messages
    const messages = document.querySelectorAll('.flash-message');
    messages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.style.display = 'none', 500);
        }, 3000);
    });

    // Validate loan form inputs
    const loanForm = document.querySelector('form[action="/loans"]');
    if (loanForm) {
        loanForm.addEventListener('submit', (e) => {
            const amount = parseFloat(document.querySelector('#amount').value);
            const duration = parseInt(document.querySelector('#duration').value);
            const interestRate = parseFloat(document.querySelector('#interest_rate').value);
            if (amount <= 0 || duration <= 0 || interestRate < 0) {
                e.preventDefault();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'flash-message error';
                errorMsg.textContent = 'Amount and duration must be positive, and interest rate cannot be negative.';
                document.querySelector('.container').prepend(errorMsg);
                setTimeout(() => {
                    errorMsg.style.opacity = '0';
                    setTimeout(() => errorMsg.remove(), 500);
                }, 3000);
            }
        });
    }

    // Validate customer form inputs
    const customerForm = document.querySelector('form[action="/customers"]');
    if (customerForm) {
        customerForm.addEventListener('submit', (e) => {
            const phone = document.querySelector('#phone').value;
            const phoneRegex = /^\+?[0-9]{10,12}$/;
            if (!phoneRegex.test(phone)) {
                e.preventDefault();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'flash-message error';
                errorMsg.textContent = 'Please enter a valid phone number (10-12 digits).';
                document.querySelector('.container').prepend(errorMsg);
                setTimeout(() => {
                    errorMsg.style.opacity = '0';
                    setTimeout(() => errorMsg.remove(), 500);
                }, 3000);
            }
        });
    }
});