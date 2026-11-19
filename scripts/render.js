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
                container.appendChild(renderVideoItem(video, { subCategory }));
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
