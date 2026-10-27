/* Initially based on https://codepen.io/tjezidzic/pen/LLWoLw */
/* Modified by Claude Sonnet 4.6 + IntersectionObserver Update by Gemini 3.5 Flash */

function makeCursor() {
    if (CURSOR === "block") {
        return "<span class='blinker blinker-block'></span>";
    } else if (CURSOR === "underline") {
        return "<span class='blinker blinker-underline'></span>";
    } else {
        return "<span class='blinker blinker-char'>" + CURSOR + "</span>";
    }
}

// 1. Move the typing logic into a reusable function
function startTypewriter(element) {
    var devTypeText = element.getAttribute("data-text") || "";

    if (REVEAL_SPEED_MS === 0) {
        element.innerHTML = devTypeText + (STAY_BLINKING ? makeCursor() : "");
        window.parent.postMessage({
            type: "terminalDone"
        }, "*");
        return;
    }

    var i = 0,
        isTag;
    (function type() {
        var text = devTypeText.slice(0, ++i);
        if (text === devTypeText) {
            element.innerHTML = text + (STAY_BLINKING ? makeCursor() : "");
            window.parent.postMessage({
                type: "terminalDone"
            }, "*");
            return;
        }
        element.innerHTML = text + makeCursor();
        var char = text.slice(-1);
        if (char === "<") isTag = true;
        if (char === ">") isTag = false;
        if (isTag) return type();
        setTimeout(type, REVEAL_SPEED_MS);
    })();
}

// 2. Set up the IntersectionObserver to trigger it on scroll
document.addEventListener("DOMContentLoaded", function() {
    var allElements = document.getElementsByClassName("typeing");

    // Define the observer configuration
    var observerOptions = {
        root: null, // Use the browser viewport
        threshold: 0.15 // Starts when 15% of the element is visible on screen
    };

    var observer = new IntersectionObserver(function(entries, observerInstance) {
        entries.forEach(function(entry) {
            // If the terminal element enters the viewport
            if (entry.isIntersecting) {
                var target = entry.target;
                setTimeout(function() { startTypewriter(target); }, START_DELAY_MS);
                // Stop watching this element so it doesn't trigger again on re-scroll
                observerInstance.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Attach the observer to all elements with the "typeing" class
    for (var j = 0; j < allElements.length; j++) {
        observer.observe(allElements[j]);
    }
});