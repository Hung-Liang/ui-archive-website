// scripts/theme.js
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark-mode') {
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
