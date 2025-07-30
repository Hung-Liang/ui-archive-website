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

    div.innerHTML = `
        <a href="${youtubeUrl}" target="_blank">
            <img src="${video.thumbnail}" alt="${video.title}" width="320">
            <p class="video-title">${video.title}</p>
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
                    tag
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
        if (videos.length === 0) {
            container.innerHTML =
                "<p style='text-align: center; margin-top: 50px;'>此月份沒有影片。</p>";
            return;
        }

        videos.forEach((video) => {
            container.appendChild(renderVideoItem(video));
        });
    })
    .catch((error) => {
        console.error("Error fetching or parsing video data:", error);
        const container = document.getElementById("video-list");
        container.innerHTML = `<p style='text-align: center; margin-top: 50px; color: red;'>無法載入此月的影片資料。</p><p style='text-align: center; color: red;'>錯誤: ${error.message}</p>`;
    });

const style = document.createElement("style");
style.textContent = `
    body {
        font-family: Arial, sans-serif;
        margin: 0; /* Reset default body margin */
        background-color: #f4f4f4;
        color: #333;
    }
    .container {
        max-width: 960px;
        margin: 20px auto; /* Center container with top/bottom margin */
        background-color: #fff;
        padding: 20px 30px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        position: relative; /* For positioning absolute elements inside */
        min-height: calc(100vh - 40px); /* Ensure container is tall enough for footer positioning */
        box-sizing: border-box; /* Include padding in height calculation */
    }

    /* New: Styles for left and right images */
    .side-image {
        position: fixed; /* Fixed position relative to viewport */
        top: 50%; /* Center vertically */
        transform: translateY(-50%); /* Adjust for vertical centering */
        z-index: -1; /* Send behind other content */
        opacity: 0.3; /* Make them semi-transparent */
        max-height: 80vh; /* Limit height for responsiveness */
        width: auto; /* Maintain aspect ratio */
    }
    .side-image.left {
        left: 20px; /* Position from left */
    }
    .side-image.right {
        right: 20px; /* Position from right */
    }

    /* Responsive adjustments for smaller screens */
    @media (max-width: 1200px) {
        .side-image {
            opacity: 0.15; /* Make them even more transparent on smaller screens */
        }
    }

    @media (max-width: 992px) {
        .side-image {
            display: none; /* Hide images completely on very small screens to save space */
        }
    }


    /* Style for top-left back button */
    .back-to-prev-button {
        position: absolute;
        top: 20px;
        left: 30px; /* Position to the left */
        display: inline-block;
        padding: 8px 15px;
        background-color: #6c757d; /* A subtle grey for back button */
        color: white;
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease, transform 0.2s ease;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        font-size: 0.9em;
        z-index: 10; /* Ensure it's above other content if overlapping */
    }
    .back-to-prev-button:hover {
        background-color: #5a6268;
        transform: translateY(-2px);
    }
    .back-to-prev-button:active {
        transform: translateY(0);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    }

    /* Styles for top-right buttons */
    .top-right-buttons {
        position: absolute;
        top: 20px;
        right: 30px;
        display: flex;
        gap: 10px;
    }
    .action-button {
        display: inline-block;
        padding: 8px 15px;
        background-color: #3498db;
        color: white;
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease, transform 0.2s ease;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        font-size: 0.9em;
    }
    .action-button:hover {
        background-color: #2980b9;
        transform: translateY(-2px);
    }
    .action-button:active {
        transform: translateY(0);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    }

    /* Footer styles */
    .footer-info {
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        width: calc(100% - 60px); /* Adjust width to fit container padding */
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8em;
        color: #777;
    }
    .developer-info {
        flex-grow: 1;
        text-align: right;
    }
    .last-update-info {
        flex-grow: 1;
        text-align: left;
    }
    .developer-info a, .last-update-info a {
        color: #777;
        text-decoration: underline;
        font-weight: normal;
    }
    .developer-info a:hover, .last-update-info a:hover {
        color: #333;
    }

    /* Video list styles */
    #video-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 20px;
        padding: 20px 0;
        margin-top: 50px; /* Adjusted to accommodate top buttons */
    }
    .video-item {
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    .video-item:hover {
        transform: translateY(-5px);
    }
    .video-item a {
        display: block;
        padding-bottom: 10px;
        color: inherit;
        text-decoration: none;
    }
    .video-item img {
        max-width: 100%;
        height: auto;
        border-bottom: 1px solid #eee;
        margin-bottom: 10px;
    }
    .video-item .video-title {
        font-weight: bold;
        padding: 0 10px;
        margin-bottom: 5px;
        color: #333;
    }
    .video-item .video-date {
        font-size: 0.9em;
        color: #666;
        padding: 0 10px;
    }
    .video-item .video-tags {
        padding: 5px 10px 10px;
        font-size: 0.8em;
        color: #555;
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 5px;
    }
    .video-item .video-tags span {
        background-color: #e0e0e0;
        padding: 3px 8px;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    .video-item .video-tags span:hover {
        background-color: #c0c0c0;
    }
`;
document.head.appendChild(style);
