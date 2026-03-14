// Modern Theme Management - ShadowNet C2 - 2026
(function() {
    'use strict';
    
    // Load theme on page load
    function loadTheme() {
        const theme = localStorage.getItem('shadownet-theme') || 'dark';
        applyTheme(theme);
    }
    
    // Apply theme to page using modern CSS classes
    function applyTheme(theme) {
        const body = document.body;
        
        // Remove both theme classes
        body.classList.remove('theme-dark', 'theme-light', 'bg-dark', 'bg-light', 'text-light', 'text-dark');
        
        // Add the selected theme class
        body.classList.add(`theme-${theme}`);
        
        // Store in localStorage
        localStorage.setItem('shadownet-theme', theme);
    }
    
    // Toggle theme
    window.toggleTheme = function() {
        const currentTheme = localStorage.getItem('shadownet-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        
        // Update theme toggle buttons if they exist
        const darkBtn = document.getElementById('theme-dark');
        const lightBtn = document.getElementById('theme-light');
        if (darkBtn && lightBtn) {
            darkBtn.checked = (newTheme === 'dark');
            lightBtn.checked = (newTheme === 'light');
        }
        
        // Show notification
        const icon = newTheme === 'dark' ? '🌙' : '☀️';
        console.log(`${icon} Theme changed to ${newTheme}`);
        
        return newTheme;
    };
    
    // Initialize theme on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadTheme);
    } else {
        loadTheme();
    }
    
    // Export for use in other scripts
    window.ShadowNetTheme = {
        load: loadTheme,
        apply: applyTheme,
        toggle: window.toggleTheme
    };
})();
