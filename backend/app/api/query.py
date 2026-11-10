"""
query.py

FastAPI router for conversational document querying and full-document summarization.
Integrates with the intent-aware RAG pipeline and maintains persistent chat history.
"""

import logging
from typing import Set

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.database.connection import get_db
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.schemas.chat import MessageCreate
from app.schemas.query import QueryRequest, QueryResponse
from app.services import chat_service, document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/{conversation_id}",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK
)
async def query_documents(
    conversation_id: int,
    query: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """
    Query the documents attached to a conversation using semantic and intent-aware RAG.
    Maintains multi-turn chat history context and provides page-level citations.
    """
    question = query.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty."
        )

    # 1. Verify conversation ownership
    chat_service.get_conversation_by_id(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )

    # 2. Retrieve documents attached to this conversation
    documents = document_service.get_chat_documents(
        db,
        user_id=current_user.id,
        conversation_id=conversation_id
    )

    # 3. Keep processed or uploaded documents owned by this user
    usable_documents = [
        doc for doc in documents
        if doc.user_id == current_user.id
        and (doc.processing_status or doc.status) in ("processed", "uploaded")
    ]

    # 4. Collect all ID representations (UUID and integer ID) for FAISS filtering
    document_ids: Set[str] = set()
    for doc in usable_documents:
        if doc.document_id:
            document_ids.add(str(doc.document_id))
        if doc.id:
            document_ids.add(str(doc.id))

    # 5. Fetch previous conversation history for conversational context
    past_messages = chat_service.get_conversation_messages(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in past_messages[-6:]
    ]

    # 6. Save the user's question to chat history
    chat_service.add_message(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        message_in=MessageCreate(
            role="user",
            content=question
        )
    )

    # 7. User-specific vector store path
    storage_dir = (
        settings.STORAGE_DIR
        / "vector_store"
        / f"user_{current_user.id}"
    )

    try:
        pipeline = RAGPipeline(
            storage_dir=str(storage_dir)
        )

        result = await pipeline.ask(
            question=question,
            top_k=max(query.top_k, 8),
            document_ids=document_ids,
            chat_history=chat_history
        )

        # 8. Save assistant response and sources to chat history
        chat_service.add_message(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            message_in=MessageCreate(
                role="assistant",
                content=result["answer"],
                source_metadata=result["sources"]
            )
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            retrieved_chunks=result["retrieved_chunks"]
        )

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Document query failed for conversation %s: %s",
            conversation_id, error
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your question. Please check the backend logs."
        ) from error


@router.post(
    "/{conversation_id}/summarize/{document_id}",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK
)
async def summarize_document(
    conversation_id: int,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """
    Dedicated endpoint to generate a full document summary across all pages.
    """
    # 1. Verify conversation ownership
    chat_service.get_conversation_by_id(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )

    # 2. Get documents attached to this conversation
    documents = document_service.get_chat_documents(
        db,
        user_id=current_user.id,
        conversation_id=conversation_id
    )

    # 3. Find the requested document (matches either document_id string or integer id)
    selected_document = next(
        (
            doc for doc in documents
            if (str(doc.document_id) == str(document_id) or str(doc.id) == str(document_id))
            and doc.user_id == current_user.id
        ),
        None
    )

    if selected_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this conversation."
        )

    storage_dir = (
        settings.STORAGE_DIR
        / "vector_store"
        / f"user_{current_user.id}"
    )

    try:
        pipeline = RAGPipeline(
            storage_dir=str(storage_dir)
        )

        # Save user request in chat
        chat_service.add_message(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            message_in=MessageCreate(
                role="user",
                content=f"Summarize document '{selected_document.original_filename or selected_document.filename}'"
            )
        )

        # Try document_id first, fallback to string(id)
        target_doc_id = selected_document.document_id or str(selected_document.id)
        try:
            result = await pipeline.summarize_document(document_id=target_doc_id)
        except ValueError:
            if selected_document.document_id and str(selected_document.id) != target_doc_id:
                result = await pipeline.summarize_document(document_id=str(selected_document.id))
            else:
                raise

        # Save assistant summary to chat
        chat_service.add_message(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            message_in=MessageCreate(
                role="assistant",
                content=result["answer"],
                source_metadata=result["sources"]
            )
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            retrieved_chunks=result["retrieved_chunks"]
        )

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Document summarization failed for conversation %s: %s",
            conversation_id, error
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to summarize the document: {error}"
        ) from error
