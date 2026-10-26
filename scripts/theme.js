// scripts/theme.js
const savedTheme = localStorage.getItem('theme');
// Without a saved preference, follow the OS setting
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
if (savedTheme === 'dark-mode' || (savedTheme === null && prefersDark)) {
    document.documentElement.classList.add('dark-mode');
}

document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        // Set initial icon based on current theme
        themeToggleBtn.innerHTML = document.documentElement.classList.contains('dark-mode') ? '☀️' : '🌙';
        
        themeToggleBtn.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark-mode');
            const isDark = document.documentElement.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark-mode' : 'light-mode');
            themeToggleBtn.innerHTML = isDark ? '☀️' : '🌙';
        });
    }
});
