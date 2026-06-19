// Этот файл отправляет сообщения в backend и потоково отображает SSE-ответы.

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button[type='submit']");
const newChatButton = document.querySelector("#new-chat");

const sessionId = getSessionId();

function createSessionId() {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }

    const randomPart = Math.random().toString(36).slice(2);
    return `session-${Date.now()}-${randomPart}`;
}

function getSessionId() {
    try {
        const savedSessionId = localStorage.getItem("chat_session_id");

        if (savedSessionId) {
            return savedSessionId;
        }

        const newSessionId = createSessionId();
        localStorage.setItem("chat_session_id", newSessionId);
        return newSessionId;
    } catch (error) {
        console.warn("Не удалось использовать localStorage", error);
        return createSessionId();
    }
}

newChatButton.addEventListener("click", () => {
    try {
        localStorage.removeItem("chat_session_id");
    } catch (error) {
        console.warn("Не удалось очистить session_id", error);
    }

    window.location.reload();
});

function addMessage(content, role, isError = false) {
    const message = document.createElement("div");
    message.className = `message message--${role}`;

    if (isError) {
        message.classList.add("message--error");
    }

    message.textContent = content;
    messages.append(message);
    messages.scrollTop = messages.scrollHeight;
    return message;
}

function readSseEvent(block) {
    let eventName = "message";
    const dataLines = [];

    for (const line of block.split(/\r?\n/)) {
        if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
        }
    }

    if (dataLines.length === 0) {
        return null;
    }

    return {
        name: eventName,
        data: JSON.parse(dataLines.join("\n")),
    };
}

function handleSseEvent(event, assistantMessage) {
    if (event.name === "token") {
        assistantMessage.textContent += event.data.text;
        messages.scrollTop = messages.scrollHeight;
        return;
    }

    if (event.name === "error") {
        throw new Error(event.data.message || "Ошибка генерации ответа");
    }
}

async function streamResponse(response, assistantMessage) {
    if (!response.body) {
        throw new Error("Браузер не поддерживает потоковые ответы");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const {value, done} = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), {stream: !done});

        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
            if (!block.trim()) {
                continue;
            }

            const event = readSseEvent(block);
            if (event) {
                handleSseEvent(event, assistantMessage);
            }
        }

        if (done) {
            break;
        }
    }

    if (buffer.trim()) {
        const event = readSseEvent(buffer);
        if (event) {
            handleSseEvent(event, assistantMessage);
        }
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const content = input.value.trim();
    if (!content) {
        return;
    }

    addMessage(content, "user");
    input.value = "";
    input.disabled = true;
    submitButton.disabled = true;

    let assistantMessage = null;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: content,
            }),
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            throw new Error(
                errorBody?.detail || `Backend returned ${response.status}`,
            );
        }

        assistantMessage = addMessage("", "assistant");
        await streamResponse(response, assistantMessage);

        if (!assistantMessage.textContent) {
            assistantMessage.remove();
            assistantMessage = null;
        }
    } catch (error) {
        console.error(error);
        const errorText = error.message || "Не удалось отправить сообщение.";

        if (assistantMessage && !assistantMessage.textContent) {
            assistantMessage.textContent = errorText;
            assistantMessage.classList.add("message--error");
        } else {
            addMessage(errorText, "assistant", true);
        }
    } finally {
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
    }
});

window.addEventListener("error", (event) => {
    console.error("Ошибка интерфейса чата", event.error || event.message);
});
