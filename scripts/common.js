function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatLastUpdate(value) {
    // Older data has no timezone; it was written in UTC by GitHub Actions
    const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/i.test(value);
    const date = new Date(hasTimezone ? value : value.replace(" ", "T") + "Z");
    if (isNaN(date)) {
        return value;
    }
    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
}

// Parses a lowercase "#" query into the tags it asks for
function parseTagQuery(videos, query) {
    const tagString = query.substring(1).trim(); // Remove '#' and trim
    // Some stored tags keep surrounding spaces, so compare them trimmed
    const isExactTag =
        tagString !== "" &&
        videos.some(
            (video) =>
                Array.isArray(video.tags) &&
                video.tags.some((tag) => String(tag).toLowerCase().trim() === tagString),
        );
    // Split by one or more spaces, and then for each part, remove any leading '#' and convert to lowercase
    const searchTags = isExactTag
        ? [tagString]
        : tagString
              .split(/\s+/)
              .filter((t) => t !== "")
              .map((t) => {
                  return t.startsWith("#") ? t.substring(1).toLowerCase() : t.toLowerCase();
              });
    return { searchTags, isExactTag };
}

function filterVideos(videos, query) {
    const normalizedQuery = query.toLowerCase().trim();
    if (normalizedQuery === "") {
        return [];
    }

    // If the query starts with '#', treat it as a tag search
    if (normalizedQuery.startsWith("#")) {
        const { searchTags, isExactTag } = parseTagQuery(videos, normalizedQuery);
        if (searchTags.length === 0) {
            return [];
        }
        return videos.filter((video) => {
            // Ensure video.tags exists and is an array
            if (!video.tags || !Array.isArray(video.tags)) {
                return false;
            }
            // Convert video's tags to lowercase for case-insensitive comparison
            const lowerCaseVideoTags = video.tags.map((tag) => {
                const lowerCaseTag = String(tag).toLowerCase();
                return isExactTag ? lowerCaseTag.trim() : lowerCaseTag;
            });
            // Check if all searchTags (which are already lowercase) are included in lowerCaseVideoTags
            return searchTags.every((searchTag) => lowerCaseVideoTags.includes(searchTag));
        });
    }

    // Otherwise, perform a title search
    return videos.filter((video) => {
        const titleMatches = video.title.toLowerCase().includes(normalizedQuery);

        // Check if any of the video's tags contain the query
        const tagsMatch =
            video.tags && Array.isArray(video.tags)
                ? video.tags.some((tag) => String(tag).toLowerCase().includes(normalizedQuery))
                : false;

        return titleMatches || tagsMatch; // Return true if title OR tags match
    });
}

// Function to render a single video item.
// subCategory is passed in because month files do not store it on each video;
// showMonth labels each card on pages that mix videos from different months.
function renderVideoItem(video, { subCategory, showMonth = false }) {
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
    const strings = translations[currentLanguage] || {};
    const viewCountText = strings["view_count"] || "views";
    const viewCountHtml = video.viewCount && subCategory !== "member" ?`<p class="video-view-count">${Number(video.viewCount).toLocaleString()} <span data-i18n="view_count">${viewCountText}</span></p>` : "";
    const monthHtml = showMonth
        ? `<p class="video-meta">(${video.year}${strings["year_suffix"] || ""}${video.month}${strings["month_suffix"] || ""})</p>`
        : "";

    div.innerHTML = `
        <a href="${youtubeUrl}" target="_blank">
            <div class="video-thumbnail-container">
                <img src="${video.thumbnail || `https://i.ytimg.com/vi/${video.videoId}/hqdefault.jpg`}" alt="${escapeHtml(video.title)}" width="320" loading="lazy" onerror="this.onerror=null;this.src='../asset/thumbnail_placeholder.svg'">
                ${durationHtml}
            </div>
            <p class="video-title">${escapeHtml(video.title)}</p>
            ${viewCountHtml}
            ${monthHtml}
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
                // For multiple tags, we'll just pass the single clicked tag.
                // User can then manually add more tags in the search bar if needed.
                window.location.href = `../pages/search_results.html?tag=${encodeURIComponent(
                    tag,
                )}`;
            });
        });
    }
    return div;
}

function loadLastUpdate(url) {
    const lastUpdateDateSpan = document.getElementById("last-update-date");
    fetch(url)
        .then((res) => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then((data) => {
            if (data && data.last_update) {
                lastUpdateDateSpan.textContent = formatLastUpdate(data.last_update);
            } else {
                lastUpdateDateSpan.textContent = "Unable to load";
                lastUpdateDateSpan.setAttribute("data-i18n", "unable_to_load");
            }
            applyTranslations();
        })
        .catch((error) => {
            console.error("Error fetching last_update.json:", error);
            lastUpdateDateSpan.textContent = "Unable to load";
            lastUpdateDateSpan.setAttribute("data-i18n", "unable_to_load");
            applyTranslations();
        });
}
