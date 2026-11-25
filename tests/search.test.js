const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

// common.js is a plain browser script, so load its functions as globals
const commonPath = path.join(__dirname, "..", "scripts", "common.js");
vm.runInThisContext(fs.readFileSync(commonPath, "utf8"), { filename: commonPath });

const VIDEOS = [
    { videoId: "rpg", title: "Morning RPG Stream", tags: ["Final Fantasy", "RPG"] },
    { videoId: "padded", title: "Padded tag", tags: [" Final Fantasy ", "Chat"] },
    { videoId: "split", title: "Separate words", tags: ["final", "fantasy"] },
    { videoId: "chat", title: "Evening talk", tags: ["Chat", "RPG"] },
    { videoId: "untagged", title: "No tags at all" },
];

function searchIds(query) {
    return filterVideos(VIDEOS, query).map((video) => video.videoId);
}

test("matches words in the title", () => {
    assert.deepEqual(searchIds("evening"), ["chat"]);
});

test("plain keywords also match part of a tag", () => {
    assert.deepEqual(searchIds("fantas"), ["rpg", "padded", "split"]);
});

test("a tag search needs the whole tag", () => {
    assert.deepEqual(searchIds("#rp"), []);
    assert.deepEqual(searchIds("#rpg"), ["rpg", "chat"]);
});

test("multiple tags must all be present", () => {
    assert.deepEqual(searchIds("#chat #rpg"), ["chat"]);
    assert.deepEqual(searchIds("#chat rpg"), ["chat"]);
    assert.deepEqual(searchIds("#chat #missing"), []);
});

test("ignores case in titles and tags", () => {
    assert.deepEqual(searchIds("EVENING"), ["chat"]);
    assert.deepEqual(searchIds("#CHAT #rPg"), ["chat"]);
});

test("a tag containing spaces matches as one tag", () => {
    assert.deepEqual(searchIds("#final fantasy"), ["rpg", "padded"]);
});

test("words are split when no tag contains the whole phrase", () => {
    assert.deepEqual(searchIds("#fantasy final"), ["split"]);
});

test("blank queries return nothing", () => {
    for (const query of ["", "   ", "#", "#   "]) {
        assert.deepEqual(searchIds(query), [], JSON.stringify(query));
    }
});

test("video dates use the site timezone", () => {
    assert.equal(formatVideoDate("2025-07-31T15:30:00Z"), new Date(2025, 7, 1).toLocaleDateString());
});
