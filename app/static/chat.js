// Этот файл отправляет сообщения из формы в backend и показывает ответы в чате.

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button[type='submit']");

const sessionId = getSessionId();

function getSessionId() {
    const savedSessionId = localStorage.getItem("chat_session_id");

    if (savedSessionId) {
        return savedSessionId;
    }

    const newSessionId = crypto.randomUUID();
    localStorage.setItem("chat_session_id", newSessionId);
    return newSessionId;
}

function addMessage(content, role, isError = false) {
    const message = document.createElement("div");
    message.className = `message message--${role}`;

    if (isError) {
        message.classList.add("message--error");
    }

    message.textContent = content;
    messages.append(message);
    messages.scrollTop = messages.scrollHeight;
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
            throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();
        addMessage(data.reply, "assistant");
    } catch (error) {
        console.error(error);
        addMessage("Не удалось отправить сообщение. Попробуйте еще раз.", "assistant", true);
    } finally {
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
    }
});
