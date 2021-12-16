scriptsContainer = document.getElementById("scripts");


// ---------- gui ----------

function pasteToFrame() {
    let frame = document.getElementById("frame");
    navigator.clipboard.readText().then(function (text) {
        frame.value = text;
    });
}

function copyFromResult() {
    let result = document.getElementById("result");
    navigator.clipboard.writeText(result.value);
}

function addScript() {
    let id = generateScriptId();

    let container = document.createElement("div");
    container.id = "script-container-" + id;
    container.classList.add("container");

    let labelContainer = document.createElement("div");
    labelContainer.id = "label-container-" + id;
    labelContainer.classList.add("label-container");

    let label = document.createElement("input");
    label.id = "label-" + id;
    label.classList.add("label");
    label.value = "script_" + id;

    let removeButton = document.createElement("button");
    removeButton.id = "remove-button-" + id;
    removeButton.classList.add("remove");
    removeButton.classList.add("right");
    removeButton.innerText = "x";
    removeButton.onclick = function () {
        removeScript(container);
    }

    labelContainer.appendChild(label);
    labelContainer.appendChild(removeButton);

    let textarea = document.createElement("textarea");
    textarea.id = "script-" + id;

    let pasteButton = document.createElement("button");
    pasteButton.id = "paste-button-" + id;
    pasteButton.classList.add("paste");
    pasteButton.classList.add("bottom-right");
    pasteButton.innerText = "p";
    pasteButton.onclick = function () {
        navigator.clipboard.readText().then(function (text) {
            textarea.value = text;
        });
    }

    container.appendChild(labelContainer);
    container.appendChild(textarea);
    container.appendChild(pasteButton);

    scriptsContainer.appendChild(container);

    refreshRemoveButtons();
    return id;
}

function removeScript(container) {
    if (scriptsContainer.childNodes.length > 1) {
        container.remove();
        refreshRemoveButtons();
    }
}

function refreshRemoveButtons() {
    removeButtons = document.getElementsByClassName("remove");
    if (scriptsContainer.childNodes.length > 1) {
        for (let i = 0; i < removeButtons.length; i++) {
            removeButtons[i].classList.remove("inactive");
        }
    }
    if (scriptsContainer.childNodes.length <= 1) {
        for (let i = 0; i < removeButtons.length; i++) {
            removeButtons[i].classList.add("inactive");
        }
    }
}

function generateScriptId() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    ).replaceAll("-", "");
}

addScript();


// ---------- compilation ----------

function compile() {
    let result = generateCompiledResult();
    let resultTextarea = document.getElementById("result");
    resultTextarea.value = result;

    document.getElementById("result-container").style = "display: block";
}

function generateCompiledResult() {
    let frame = document.getElementById("frame").value;
    let frameParts = frame.split("#$content$");

    let result = "";
    result += frameParts[0] + "\n";

    let containers = document.getElementsByClassName("container");
    for (let i = 0; i < containers.length; i++) {
        let container = containers[i];
        let id = container.id.split("-")[2];
        let name = document.getElementById("label-" + id).value;

        let script = document.getElementById("script-" + id).value;
        let scriptContents = script.split("#$start$")[1];

        result += "\n# ---------- " + name + " ----------\n\n" + scriptContents + "\n";
    }

    result += "\n" + frameParts[1];
    return result;
}


// ---------- notes ----------

notesVisible = false;
function toggleNotes() {
    let notesContainer = document.getElementById("notes-container");
    notesVisible = !notesVisible;
    if (notesVisible) {
        notesContainer.style = "display: block";
    } else {
        notesContainer.style = "display: none";
    }
}


// ---------- save ----------

function saveToClipboard() {
    let saveString = generateSaveString();
    navigator.clipboard.writeText(saveString);
}

function readFromClipboard() {
    navigator.clipboard.readText().then(processSaveStringFromClipboard);
    console.log("....");
}
function processSaveStringFromClipboard(saveString) {
    console.log("processing save string...");
    readSaveString(saveString.toString());
}

function generateSaveString() {
    let result = "";

    let frame = document.getElementById("frame").value;
    result += "frame§" + frame;

    let containers = document.getElementsByClassName("container");
    for (let i = 0; i < containers.length; i++) {
        let container = containers[i];
        let id = container.id.split("-")[2];
        let name = document.getElementById("label-" + id).value;
        let script = document.getElementById("script-" + id).value;
        result += "§" + name + "§" + script;
    }

    return result;
}

function readSaveString(saveString) {
    let confirmed = confirm("Do you want to overwrite the current project?");
    if (!confirmed) {
        console.log("cancelled")
        return;
    }
    console.log("reading save string: \"" + saveString + "\"");

    for (let container of document.getElementsByClassName("container")) {
        container.remove();
    }
    refreshRemoveButtons();

    let cache_name = "";
    let first = true;
    for (let part of saveString.split("§")) {
        if (first) {
            cache_name = part;
            first = false;
        } else {
            let name = cache_name;
            let script = part;

            if (name === "frame") {
                console.log("frame: " + script);
                document.getElementById("frame").value = script;
            } else {
                console.log("script " + name + ": " + script);
                let id = addScript();
                document.getElementById("label-" + id).value = name;
                document.getElementById("script-" + id).value = script;
            }

            cache_name = "";
            first = true;
        }
    }
}