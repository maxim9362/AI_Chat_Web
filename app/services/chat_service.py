# Этот файл управляет сохранением диалога и потоковой генерацией ответа AI.

from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.config import settings
from app.llm.client import LLMClient
from app.rag.embeddings import EmbeddingClient
from app.rag.retriever import KnowledgeRetriever, RetrievedChunk
from app.repositories.message_repository import (
    get_recent_messages,
    save_message,
)
from app.services.prompt_builder import build_chat_prompt
from app.services.conversation_responder import get_conversation_response
from app.services.lead_dialogue import process_lead_dialogue
from app.services.session_service import get_or_create_session


HISTORY_LIMIT = 6
LEAD_HISTORY_LIMIT = 30
NO_KNOWLEDGE_RESPONSE = (
    "По этому вопросу лучше связаться со специалистом компании."
)


def stream_chat_answer(
    db: Session,
    llm_client: LLMClient,
    session_id: str,
    user_message: str,
) -> AsyncIterator[str]:
    chat_session = get_or_create_session(db, session_id)
    saved_user_message = save_message(
        db=db,
        session_id=chat_session.session_id,
        role="user",
        content=user_message,
    )

    recent_messages = get_recent_messages(
        db=db,
        session_id=chat_session.session_id,
        limit=LEAD_HISTORY_LIMIT,
    )
    history = [
        message
        for message in recent_messages
        if message.id != saved_user_message.id
    ][-HISTORY_LIMIT:]
    lead_dialogue_response = process_lead_dialogue(
        db=db,
        session_id=chat_session.session_id,
        messages=recent_messages,
    )

    conversation_response = (
        lead_dialogue_response
        or get_conversation_response(user_message)
    )
    knowledge_chunks = []
    if conversation_response is None:
        embedding_client = EmbeddingClient(
            model_name=settings.embedding_model_name,
        )
        retriever = KnowledgeRetriever(
            chroma_path=settings.chroma_path,
            collection_name=settings.chroma_collection,
            embedding_client=embedding_client,
            max_distance=settings.rag_max_distance,
        )
        knowledge_chunks = retriever.retrieve(user_message, limit=5)
        previous_user_messages = [
            message.content
            for message in history
            if message.role == "user"
        ]
        if _needs_contextual_retrieval(user_message) and previous_user_messages:
            contextual_query = (
                f"{previous_user_messages[-1]}\n"
                f"Уточнение пользователя: {user_message}"
            )
            contextual_chunks = retriever.retrieve(contextual_query, limit=5)
            knowledge_chunks = _merge_knowledge_chunks(
                knowledge_chunks,
                contextual_chunks,
                limit=5,
            )

    async def generate() -> AsyncIterator[str]:
        if conversation_response is not None:
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=conversation_response,
            )
            yield conversation_response
            return

        if not knowledge_chunks:
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=NO_KNOWLEDGE_RESPONSE,
            )
            yield NO_KNOWLEDGE_RESPONSE
            return

        prompt = build_chat_prompt(
            history=history,
            user_question=user_message,
            knowledge_chunks=[chunk.content for chunk in knowledge_chunks],
        )
        answer_parts: list[str] = []

        async for chunk in llm_client.stream_answer(
            system_prompt=prompt.system_prompt,
            messages=prompt.messages,
        ):
            answer_parts.append(chunk)
            yield chunk

        full_answer = "".join(answer_parts).strip()
        if full_answer:
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=full_answer,
            )

    return generate()


def _needs_contextual_retrieval(message: str) -> bool:
    normalized_message = message.casefold()
    context_markers = (
        "с ним",
        "с ней",
        "это",
        "этот",
        "эта",
        "они",
        "там",
        "подробнее",
    )
    return len(normalized_message) <= 80 and any(
        marker in normalized_message
        for marker in context_markers
    )


def _merge_knowledge_chunks(
    primary_chunks: list[RetrievedChunk],
    contextual_chunks: list[RetrievedChunk],
    limit: int,
) -> list[RetrievedChunk]:
    chunks_by_source: dict[str, RetrievedChunk] = {}
    for chunk in [*primary_chunks, *contextual_chunks]:
        existing = chunks_by_source.get(chunk.source)
        if existing is None or chunk.distance < existing.distance:
            chunks_by_source[chunk.source] = chunk

    return sorted(
        chunks_by_source.values(),
        key=lambda chunk: chunk.distance,
    )[:limit]
