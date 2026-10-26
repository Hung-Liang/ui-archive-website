const params = new URLSearchParams(window.location.search);
const category = params.get("cat");
const subCategory = params.get("sub");
const year = params.get("y");
const month = String(params.get("m")).padStart(2, "0");

// Removed tag popup related elements and logic as it's now handled by redirection to search_results.html

const SUB_CATEGORY_KEYS = { normal: "stream_category", member: "member_only_category" };

// Title and scope are i18n templates, so a language switch re-renders them
function renderMonthHeading(videoCount) {
    const title = document.getElementById("month-title");
    title.setAttribute("data-i18n", "month_heading");
    title.setAttribute("data-i18n-vars", JSON.stringify({ year, month: Number(month) }));

    const scope = document.getElementById("month-scope");
    if (SUB_CATEGORY_KEYS[subCategory]) {
        scope.setAttribute("data-i18n", SUB_CATEGORY_KEYS[subCategory]);
    }

    if (videoCount !== undefined) {
        const count = document.getElementById("month-count");
        count.setAttribute("data-i18n", "video_count");
        count.setAttribute("data-i18n-vars", JSON.stringify({ count: videoCount }));
        count.before(" · ");
    }
    applyTranslations();
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function renderVideoItem(video) {
    const div = document.createElement("div");
    div.className = "video-item";
    const youtubeUrl = `https://www.youtube.com/watch?v=${video.videoId}`;

    let tagsHtml = "";
    if (video.tags && video.tags.length > 0) {
        tagsHtml =
            `<div class="video-tags">` +
            video.tags
                .map((tag) => `<span data-tag="${escapeHtml(String(tag).toLowerCase())}">${escapeHtml(tag)}</span>`)
                .join("") +
            `</div>`;
    }

    const durationHtml = video.duration ? `<span class="video-duration">${video.duration}</span>` : "";
    const viewCountText = (translations[currentLanguage] && translations[currentLanguage]["view_count"]) || "views";
    const viewCountHtml = video.viewCount ? `<p class="video-view-count">${Number(video.viewCount).toLocaleString()} <span data-i18n="view_count">${viewCountText}</span></p>` : "";

    div.innerHTML = `
        <a href="${youtubeUrl}" target="_blank">
            <div class="video-thumbnail-container">
                <img src="${video.thumbnail}" alt="${escapeHtml(video.title)}" width="320" loading="lazy" onerror="this.onerror=null;this.src='../asset/thumbnail_placeholder.svg'">
                ${durationHtml}
            </div>
            <p class="video-title">${escapeHtml(video.title)}</p>
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

function loadMonthVideos() {
    return fetch(`../data/${category}/${subCategory}/${year}/${month}.json`)
        .then((res) => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status} for ${res.url}`);
            }
            return res.json();
        })
        .then((videos) => {
            const container = document.getElementById("video-list");
            container.innerHTML = ""; // Clear skeleton loaders
            renderMonthHeading(videos.length);
            if (videos.length === 0) {
                container.innerHTML = `<p class='list-message' data-i18n="no_videos_this_month">No videos available for this month.</p>`;
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
            renderMonthHeading();
            container.innerHTML = `<p class='list-message error'><span data-i18n="unable_to_load_video_data">Unable to load video data for this month.</span><br>Error: ${escapeHtml(error.message)}</p>`;
            applyTranslations(); // Apply translations to the error message
        });
}
