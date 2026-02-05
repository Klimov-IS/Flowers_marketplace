/**
 * Catalog Page Prototype - Interactive Demo
 */

document.addEventListener('DOMContentLoaded', () => {
    // Filter chips toggle
    const chips = document.querySelectorAll('.filter-chips .chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            // Find all chips in same group
            const group = chip.parentElement;
            group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
        });
    });

    // Color buttons toggle
    const colorBtns = document.querySelectorAll('.color-btn');
    colorBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.classList.toggle('active');
        });
    });

    // Quantity controls
    document.querySelectorAll('.quantity-row').forEach(row => {
        const minusBtn = row.querySelector('.qty-btn:first-child');
        const plusBtn = row.querySelector('.qty-btn:last-child');
        const input = row.querySelector('.qty-input');

        minusBtn.addEventListener('click', () => {
            const val = parseInt(input.value) || 1;
            if (val > 1) input.value = val - 1;
        });

        plusBtn.addEventListener('click', () => {
            const val = parseInt(input.value) || 1;
            input.value = val + 1;
        });
    });

    // Add to cart buttons
    document.querySelectorAll('.btn-add-cart').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.product-card');
            const title = card.querySelector('.product-title').textContent;
            const qty = card.querySelector('.qty-input').value;

            // Update cart count
            const cartCount = document.querySelector('.cart-count');
            const currentCount = parseInt(cartCount.textContent) || 0;
            cartCount.textContent = currentCount + parseInt(qty);

            // Show feedback
            btn.textContent = 'Добавлено!';
            btn.style.background = 'var(--success)';

            setTimeout(() => {
                btn.textContent = 'В корзину';
                btn.style.background = '';
            }, 1500);

            console.log(`Added to cart: ${title} x ${qty}`);
        });
    });

    // Mobile filter toggle
    const mobileFilterBtn = document.querySelector('.mobile-filter-btn');
    const filtersSidebar = document.querySelector('.filters-sidebar');

    if (mobileFilterBtn && filtersSidebar) {
        mobileFilterBtn.addEventListener('click', () => {
            filtersSidebar.classList.toggle('show');
        });
    }

    // Reset filters
    const resetBtn = document.querySelector('.btn-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // Reset chips
            document.querySelectorAll('.filter-chips .chip').forEach((chip, i) => {
                chip.classList.toggle('active', i === 0);
            });

            // Reset checkboxes
            document.querySelectorAll('.filter-checkbox input').forEach(cb => {
                cb.checked = false;
            });

            // Reset colors
            document.querySelectorAll('.color-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            // Reset ranges
            document.querySelectorAll('.range-input').forEach(input => {
                input.value = input.min || input.getAttribute('value');
            });

            // Reset toggle
            const toggle = document.querySelector('.filter-toggle input');
            if (toggle) toggle.checked = true;
        });
    }

    // Pagination demo
    document.querySelectorAll('.pagination-num').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pagination-num').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Search demo
    const searchInput = document.querySelector('.search-large input');
    const resultsCount = document.querySelector('.results-count strong');

    if (searchInput && resultsCount) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase();
            const cards = document.querySelectorAll('.product-card');
            let visibleCount = 0;

            cards.forEach(card => {
                const title = card.querySelector('.product-title').textContent.toLowerCase();
                const colors = card.querySelector('.product-colors').textContent.toLowerCase();
                const country = card.querySelector('.country-name').textContent.toLowerCase();

                const matches = !query ||
                    title.includes(query) ||
                    colors.includes(query) ||
                    country.includes(query);

                card.style.display = matches ? '' : 'none';
                if (matches) visibleCount++;
            });

            resultsCount.textContent = visibleCount;
        });
    }
});
