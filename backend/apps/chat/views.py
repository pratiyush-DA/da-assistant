import json

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from services.graphrag.citations import chunk_display_label
from services.langchain.streaming import retrieve_and_fit_context, stream_rag_tokens
from services.neo4j.repositories.conversation import ConversationRepository

from .serializers import ChatMessageSerializer, ChatRequestSerializer


def _chunks_to_sources(chunks) -> list[dict]:
    return [
        {
            "id": c.id,
            "section_header": c.section_header,
            "page_number": c.page_number,
            "document_id": c.document_id,
            "source": c.source,
            "chunk_type": c.chunk_type,
            "display_label": chunk_display_label(c),
        }
        for c in chunks
    ]


class ChatStreamView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_id = str(serializer.validated_data["client_id"])
        user_id = str(serializer.validated_data["user_id"])
        message = serializer.validated_data["message"]
        conv_repo = ConversationRepository()

        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            conversation_id = str(conversation_id)
        else:
            conv = conv_repo.create(
                user_id=user_id,
                client_id=client_id,
                title="New chat",
            )
            conversation_id = conv["id"]

        conv_repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )
        messages = conv_repo.list_messages(conversation_id)
        user_msgs = [m for m in messages if m["role"] == "user"]
        if len(user_msgs) == 1:
            title = message.strip()[:60] or "New chat"
            conv_repo.set_title(conversation_id, title)

        rag_result = retrieve_and_fit_context(client_id, message)
        sources = _chunks_to_sources(rag_result.citation_chunks)

        def event_stream():
            meta = json.dumps({"conversation_id": conversation_id})
            yield f"data: {meta}\n\n"
            if not settings.GROQ_API_KEY:
                err = json.dumps({"error": "GROQ_API_KEY is not configured."})
                yield f"data: {err}\n\n"
                return
            full_response = []
            try:
                for token in stream_rag_tokens(
                    message,
                    rag_result.context,
                    use_dictionary_prompt=rag_result.use_dictionary,
                    use_mixed_prompt=rag_result.use_mixed,
                ):
                    full_response.append(token)
                    payload = json.dumps({"token": token})
                    yield f"data: {payload}\n\n"
            except Exception as exc:
                err = json.dumps({"error": str(exc)})
                yield f"data: {err}\n\n"
                return

            assistant_text = "".join(full_response)
            conv_repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text,
                sources=sources,
            )
            done = json.dumps(
                {"done": True, "sources": sources, "conversation_id": conversation_id}
            )
            yield f"data: {done}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["X-Conversation-Id"] = conversation_id
        return response


class ChatHistoryView(APIView):
    """Deprecated: use GET /api/conversations/{id}/messages/"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        client_id = request.query_params.get("client_id")
        user_id = request.query_params.get("user_id")
        if not client_id:
            return Response({"detail": "client_id is required."}, status=400)
        conv_repo = ConversationRepository()
        if user_id:
            convos = conv_repo.list_for_user_client(str(user_id), str(client_id))
            if not convos:
                return Response([])
            messages = conv_repo.list_messages(convos[0]["id"])
            return Response(ChatMessageSerializer(messages, many=True).data)
        from services.neo4j.repositories import ChatRepository

        messages = ChatRepository().list_by_client(client_id)
        return Response(ChatMessageSerializer(messages, many=True).data)
