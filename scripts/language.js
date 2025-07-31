// language.js
let translations = {};
let currentLanguage = localStorage.getItem("language") || "en"; // Default to English

const languageMap = {
    en: "English",
    "zh-TW": "繁體中文",
    jp: "日本語",
};

async function loadTranslations() {
    try {
        // Correct the path to access the locales folder from the parent directory
        const response = await fetch(`../locales/${currentLanguage}.json`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        translations[currentLanguage] = await response.json();

        // Load other languages if needed, or just the current one
        // Ensure paths are correct for all fetches
        if (currentLanguage !== "en") {
            const enResponse = await fetch("../locales/en.json");
            if (enResponse.ok) {
                translations["en"] = await enResponse.json();
            }
        }
        if (currentLanguage !== "zh-TW") {
            const zhTwResponse = await fetch("../locales/zh-TW.json");
            if (zhTwResponse.ok) {
                translations["zh-TW"] = await zhTwResponse.json();
            }
        }
    } catch (error) {
        console.error("Error loading translations:", error);
        // Fallback to English if loading fails
        currentLanguage = "en";
        const fallbackResponse = await fetch("../locales/en.json"); // Corrected path for fallback
        if (fallbackResponse.ok) {
            translations["en"] = await fallbackResponse.json();
        }
    }
}

function applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
        const key = element.getAttribute("data-i18n");
        if (translations[currentLanguage] && translations[currentLanguage][key]) {
            element.textContent = translations[currentLanguage][key];
        } else if (translations["en"] && translations["en"][key]) {
            // Fallback to English
            element.textContent = translations["en"][key];
        }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
        const key = element.getAttribute("data-i18n-placeholder");
        if (translations[currentLanguage] && translations[currentLanguage][key]) {
            element.placeholder = translations[currentLanguage][key];
        } else if (translations["en"] && translations["en"][key]) {
            // Fallback to English
            element.placeholder = translations["en"][key];
        }
    });

    // Update document title
    const titleElement = document.querySelector("title");
    const titleKey = titleElement.getAttribute("data-i18n");
    if (titleKey && translations[currentLanguage] && translations[currentLanguage][titleKey]) {
        titleElement.textContent = translations[currentLanguage][titleKey];
    } else if (titleKey && translations["en"] && translations["en"][titleKey]) {
        titleElement.textContent = translations["en"][titleKey];
    }
}

function setupLanguageSelector() {
    const selectElement = document.getElementById("language-select");
    if (selectElement) {
        // Clear existing options
        selectElement.innerHTML = "";

        // Add options from languageMap
        for (const langCode in languageMap) {
            const option = document.createElement("option");
            option.value = langCode;
            option.textContent = languageMap[langCode];
            selectElement.appendChild(option);
        }

        selectElement.value = currentLanguage;

        selectElement.addEventListener("change", async (event) => {
            currentLanguage = event.target.value;
            localStorage.setItem("language", currentLanguage);
            await loadTranslations();
            applyTranslations();
        });
    }
}

// Ensure the language selector is set up after the DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    setupLanguageSelector();
});

// Expose functions to the global scope if needed by other scripts
window.loadTranslations = loadTranslations;
window.applyTranslations = applyTranslations;
window.currentLanguage = currentLanguage; // Make currentLanguage accessible
window.translations = translations; // Make translations accessible
