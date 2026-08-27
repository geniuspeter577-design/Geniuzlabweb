"""Tests for the ai_hub app: AI Chat, AI Image Generator, AI Video
Generator. None of these hit real external APIs — every provider call
is mocked, so this suite runs offline and never spends API credits.

This app had no tests.py at all before this suite (like every other
app in the project — see CHANGELOG.md / README.md "Known limitations").
It's scoped to ai_hub specifically because that's the app most changed
in this pass; it is not a claim that the rest of the project is tested.
"""

import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ChatConversation, ChatMessage, GeneratedImage, GeneratedVideo

User = get_user_model()


def make_user(username="creativeuser"):
    # User.email has a DB-level unique=True constraint (see
    # accounts/migrations/0005_user_email_unique.py). Several tests create
    # more than one user in the same test (e.g. owner/other), so each user
    # needs its own non-blank email or the second create_user() collides.
    return User.objects.create_user(username=username, password="testpass123", email=f"{username}@test.com")


class AiHubHomeTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_home_requires_login(self):
        response = self.client.get(reverse("ai_hub"))
        self.assertEqual(response.status_code, 302)

    def test_home_renders_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ai_hub"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("chat_configured", response.context)
        self.assertIn("image_configured", response.context)
        self.assertIn("video_configured", response.context)


class ChatModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_display_title_falls_back_when_blank(self):
        conv = ChatConversation.objects.create(user=self.user)
        self.assertEqual(conv.display_title(), "New conversation")

    def test_display_title_uses_title_when_set(self):
        conv = ChatConversation.objects.create(user=self.user, title="Logo ideas")
        self.assertEqual(conv.display_title(), "Logo ideas")

    def test_messages_ordered_oldest_first(self):
        conv = ChatConversation.objects.create(user=self.user)
        ChatMessage.objects.create(conversation=conv, role="user", content="first")
        ChatMessage.objects.create(conversation=conv, role="assistant", content="second")
        contents = list(conv.messages.values_list("content", flat=True))
        self.assertEqual(contents, ["first", "second"])

    def test_conversations_ordered_most_recently_updated_first(self):
        older = ChatConversation.objects.create(user=self.user, title="older")
        newer = ChatConversation.objects.create(user=self.user, title="newer")
        ids = list(ChatConversation.objects.filter(user=self.user).values_list("pk", flat=True))
        self.assertEqual(ids, [newer.pk, older.pk])


class ChatViewAccessTests(TestCase):
    """A conversation belongs to exactly one user — these prove that
    holds even when someone else guesses/tries a valid pk."""

    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("other")
        self.conversation = ChatConversation.objects.create(user=self.owner, title="Private thread")

    def test_chat_list_requires_login(self):
        response = self.client.get(reverse("ai_hub_chat_list"))
        self.assertEqual(response.status_code, 302)

    def test_owner_can_view_conversation(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("ai_hub_chat_conversation", args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_view_conversation(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("ai_hub_chat_conversation", args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_send_into_conversation(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("ai_hub_chat_send", args=[self.conversation.pk]),
            data=json.dumps({"message": "hi"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_delete_conversation(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("ai_hub_chat_delete", args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ChatConversation.objects.filter(pk=self.conversation.pk).exists())

    def test_owner_can_delete_own_conversation(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("ai_hub_chat_delete", args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ChatConversation.objects.filter(pk=self.conversation.pk).exists())


class ChatEntryPointTests(TestCase):
    """chat_list is the AI Hub Chat entry point (sidebar layout) — it
    should behave like ChatGPT's root route: drop straight into the
    most recent conversation if one exists, otherwise show the empty
    landing state (still with the sidebar/new-chat button)."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_no_conversations_shows_landing_state(self):
        response = self.client.get(reverse("ai_hub_chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["conversation"])

    def test_existing_conversation_redirects_to_most_recent(self):
        ChatConversation.objects.create(user=self.user, title="older")
        newer = ChatConversation.objects.create(user=self.user, title="newer")
        response = self.client.get(reverse("ai_hub_chat_list"))
        self.assertRedirects(response, reverse("ai_hub_chat_conversation", args=[newer.pk]))

    def test_entry_point_never_leaks_another_users_conversation(self):
        other = make_user("someone_else")
        ChatConversation.objects.create(user=other, title="not yours")
        response = self.client.get(reverse("ai_hub_chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["conversation"])


class ChatNewConversationTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ai_hub_chat_new"))
        self.assertEqual(response.status_code, 405)

    def test_post_creates_conversation_and_redirects(self):
        self.client.force_login(self.user)
        self.assertEqual(ChatConversation.objects.count(), 0)
        response = self.client.post(reverse("ai_hub_chat_new"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ChatConversation.objects.count(), 1)
        conv = ChatConversation.objects.first()
        self.assertEqual(conv.user, self.user)


class ChatSendApiTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.conversation = ChatConversation.objects.create(user=self.user)
        self.url = reverse("ai_hub_chat_send", args=[self.conversation.pk])
        self.client.force_login(self.user)

    def test_empty_message_rejected(self):
        response = self.client.post(self.url, data=json.dumps({"message": "   "}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])

    @patch.dict("os.environ", {}, clear=True)
    def test_not_configured_when_no_api_key(self):
        response = self.client.post(
            self.url, data=json.dumps({"message": "hello"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertTrue(data.get("not_configured"))
        # The user's turn must NOT be silently lost even though the
        # provider isn't configured yet — the whole point of persisting
        # user data (per the project brief) is that nothing disappears.
        self.assertFalse(ChatMessage.objects.filter(conversation=self.conversation).exists())

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"})
    @patch("ai_hub.views.stream_chat_reply")
    def test_streaming_reply_is_saved_after_completion(self, mock_stream):
        mock_stream.return_value = iter(["Hello", " there", "!"])

        response = self.client.post(
            self.url, data=json.dumps({"message": "hi"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        # StreamingHttpResponse doesn't expose `.content` — it must be
        # consumed from `.streaming_content` to actually run the
        # generator (and this is what saves the assistant's message).
        body = b"".join(response.streaming_content).decode()
        self.assertIn('"chunk"', body)
        self.assertIn('"done": true', body)

        self.conversation.refresh_from_db()
        messages = list(self.conversation.messages.order_by("created_at"))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "hi")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, "Hello there!")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"})
    def test_conversation_title_set_from_first_message(self):
        self.assertEqual(self.conversation.title, "")
        with patch("ai_hub.views.stream_chat_reply", return_value=iter(["ok"])):
            self.client.post(
                self.url,
                data=json.dumps({"message": "Design me a logo for a coffee shop"}),
                content_type="application/json",
            )
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.title, "Design me a logo for a coffee shop")


class ChatProviderUnitTests(TestCase):
    """Directly exercises ai_hub/chat_provider.py without Django's test
    client, mocking the HTTP layer so no real network call is made."""

    @patch.dict("os.environ", {}, clear=True)
    def test_is_chat_configured_false_without_key(self):
        from .chat_provider import is_chat_configured
        self.assertFalse(is_chat_configured())

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    def test_is_chat_configured_true_with_key(self):
        from .chat_provider import is_chat_configured
        self.assertTrue(is_chat_configured())

    @patch.dict("os.environ", {}, clear=True)
    def test_stream_chat_reply_raises_when_not_configured(self):
        from .chat_provider import ChatProviderNotConfigured, stream_chat_reply
        with self.assertRaises(ChatProviderNotConfigured):
            list(stream_chat_reply([{"role": "user", "content": "hi"}]))

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("ai_hub.chat_provider.requests.post")
    def test_stream_chat_reply_parses_sse_chunks(self, mock_post):
        from .chat_provider import stream_chat_reply

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hel"}}]}',
            'data: {"choices":[{"delta":{"content":"lo"}}]}',
            "data: [DONE]",
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = sse_lines
        mock_post.return_value = mock_response

        chunks = list(stream_chat_reply([{"role": "user", "content": "hi"}]))
        self.assertEqual(chunks, ["Hel", "lo"])

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("ai_hub.chat_provider.requests.post")
    def test_stream_chat_reply_raises_on_http_error(self, mock_post):
        from .chat_provider import ChatGenerationError, stream_chat_reply

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "server error"
        mock_post.return_value = mock_response

        with self.assertRaises(ChatGenerationError):
            list(stream_chat_reply([{"role": "user", "content": "hi"}]))


class ImageGeneratorTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    @patch.dict("os.environ", {}, clear=True)
    def test_not_configured_response(self):
        response = self.client.post(
            reverse("ai_hub_image_generate"),
            data=json.dumps({"prompt": "a cat"}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertTrue(data.get("not_configured"))

    def test_empty_prompt_rejected(self):
        response = self.client.post(
            reverse("ai_hub_image_generate"),
            data=json.dumps({"prompt": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("ai_hub.providers.requests.post")
    def test_successful_generation_creates_record(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
        mock_post.return_value = mock_response

        response = self.client.post(
            reverse("ai_hub_image_generate"),
            data=json.dumps({"prompt": "a cat wearing sunglasses"}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        self.assertEqual(GeneratedImage.objects.count(), 1)
        record = GeneratedImage.objects.first()
        self.assertEqual(record.status, "done")
        self.assertEqual(record.user, self.user)


class VideoGeneratorTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    @patch.dict("os.environ", {}, clear=True)
    def test_not_configured_response(self):
        response = self.client.post(
            reverse("ai_hub_video_generate"),
            data=json.dumps({"prompt": "a cinematic advert"}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertTrue(data.get("not_configured"))

    @patch.dict("os.environ", {"RUNWAY_API_KEY": "key-test"})
    @patch("ai_hub.video_providers.requests.post")
    def test_successful_start_creates_record(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "job-123"}
        mock_post.return_value = mock_response

        response = self.client.post(
            reverse("ai_hub_video_generate"),
            data=json.dumps({"prompt": "a 15-second animation"}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        record = GeneratedVideo.objects.first()
        self.assertEqual(record.external_job_id, "job-123")
        self.assertEqual(record.status, "processing")

    def test_status_check_requires_ownership(self):
        other = make_user("other_video_user")
        video = GeneratedVideo.objects.create(
            user=other, prompt="x", provider="runway", status="processing"
        )
        response = self.client.get(reverse("ai_hub_video_status", args=[video.pk]))
        self.assertEqual(response.status_code, 404)
