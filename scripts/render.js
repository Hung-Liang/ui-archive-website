const params = new URLSearchParams(window.location.search);
const category = params.get("cat");
const subCategory = params.get("sub");
const year = params.get("y");
const month = String(params.get("m")).padStart(2, "0");

// Removed tag popup related elements and logic as it's now handled by redirection to search_results.html

function renderVideoItem(video) {
    const div = document.createElement("div");
    div.className = "video-item";
    const youtubeUrl = `https://www.youtube.com/watch?v=${video.videoId}`;

    let tagsHtml = "";
    if (video.tags && video.tags.length > 0) {
        tagsHtml =
            `<div class="video-tags">` +
            video.tags
                .map((tag) => `<span data-tag="${String(tag).toLowerCase()}">${tag}</span>`)
                .join("") +
            `</div>`;
    }

    const durationHtml = video.duration ? `<span class="video-duration">${video.duration}</span>` : "";
    const viewCountText = (window.translations[window.currentLanguage] && window.translations[window.currentLanguage]["view_count"]) || "views";
    const viewCountHtml = video.viewCount ? `<p class="video-view-count">${Number(video.viewCount).toLocaleString()} ${viewCountText}</p>` : "";

    div.innerHTML = `
        <a href="${youtubeUrl}" target="_blank">
            <div class="video-thumbnail-container">
                <img src="${video.thumbnail}" alt="${video.title}" width="320" loading="lazy">
                ${durationHtml}
            </div>
            <p class="video-title">${video.title}</p>
            ${viewCountHtml}
            <p class="video-date">${new Date(video.publishedAt).toLocaleDateString()}</p>
        </a>
        ${tagsHtml}
    `;

    // Add event listeners for tags to redirect to search_results.html
    if (video.tags && video.tags.length > 0) {
        div.querySelectorAll(".video-tags span").forEach((tagSpan) => {
            tagSpan.addEventListener("click", (event) => {
                event.preventDefault(); // Prevent default link behavior
                event.stopPropagation(); // Stop event bubbling
                const tag = tagSpan.dataset.tag; // This tag is already lowercase
                // Redirect to search_results.html with the tag as a query parameter
                window.location.href = `../pages/search_results.html?tag=${encodeURIComponent(
                    tag,
                )}`;
            });
        });
    }
    return div;
}

fetch(`../data/${category}/${subCategory}/${year}/${month}.json`)
    .then((res) => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status} for ${res.url}`);
        }
        return res.json();
    })
    .then((videos) => {
        const container = document.getElementById("video-list");
        container.innerHTML = ""; // Clear skeleton loaders
        if (videos.length === 0) {
            container.innerHTML = `<p style='text-align: center; margin-top: 50px;' data-i18n="no_videos_this_month">No videos available for this month.</p>`;
            applyTranslations(); // Apply translations to the new content
            return;
        }

        videos.forEach((video) => {
            container.appendChild(renderVideoItem(video));
        });
    })
    .catch((error) => {
        console.error("Error fetching or parsing video data:", error);
        const container = document.getElementById("video-list");
        container.innerHTML = `<p style='text-align: center; margin-top: 50px; color: red;' data-i18n="unable_to_load_video_data">Unable to load video data for this month.</p><p style='text-align: center; color: red;'>Error: ${error.message}</p>`;
        applyTranslations(); // Apply translations to the error message
    });
