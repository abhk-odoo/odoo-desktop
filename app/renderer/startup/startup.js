document.addEventListener('DOMContentLoaded', async function () {
    const form = document.getElementById('url_form');
    const urlInput = document.getElementById('domain_url');
    const loadButton = document.getElementById('load_button');
    const buttonText = document.querySelector('.button-text');
    const spinner = document.querySelector('.spinner');

    // Load and display domain history
    await checkDomainHistory();

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const url = urlInput.value.trim();

        if (!url) {
            showError('Please enter a valid URL');
            return;
        }

        try {
            new URL(url);
        } catch (error) {
            showError('Please enter a valid URL format');
            return;
        }

        setLoadingState(true);

        if (window.domain && window.domain.load_domain) {
            try {
                // Save domain to history before loading
                window.domain.save_domain(url);
                const loadResult = await window.domain.load_domain(url);

                if (!loadResult) {
                    showError('Failed to connect to the Odoo. URL may be unreachable.');
                    setLoadingState(false);
                    return;
                }
            } catch (error) {
                showError('Failed to load the POS application. Please check the URL and try again.');
                setLoadingState(false);
            }
        } else {
            setTimeout(() => {
                setLoadingState(false);
            }, 2000);
        }
    });

    urlInput.addEventListener('input', function () {
        clearError();
    });

    function setLoadingState(loading) {
        if (loading) {
            loadButton.disabled = true;
            loadButton.classList.add('loading');
            buttonText.textContent = 'Loading...';
            spinner.style.display = 'block';
        } else {
            loadButton.disabled = false;
            loadButton.classList.remove('loading');
            buttonText.textContent = 'Connect';
            spinner.style.display = 'none';
        }
    }

    function showError(message) {
        urlInput.classList.add('error');

        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            urlInput.parentNode.appendChild(errorDiv);
        }

        errorDiv.textContent = message;
        errorDiv.classList.add('show');

        urlInput.focus();
    }

    function clearError() {
        urlInput.classList.remove('error');
        const errorDiv = document.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.classList.remove('show');
        }
    }

    // Auto-focus the input when page loads
    setTimeout(() => {
        urlInput.focus();
    }, 500);

    async function checkDomainHistory() {
        if (!window.domain || !window.domain.get_domain_history) {
            return;
        }

        try {
            const savedDomain = await window.domain.get_domain_history();

            if (savedDomain && savedDomain.url) {
                urlInput.value = savedDomain.url;
            } else {
                urlInput.value = "";
            }
        } catch (error) {
            console.error('Failed to load domain history:', error);
        }
    }
});
