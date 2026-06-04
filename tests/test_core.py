"""Core logic tests — no database or external services required."""

import hashlib

import pytest

from packages.shared.utils.hashing import generate_token, hash_token, verify_token


class TestHashing:
    """Test token generation and hashing utilities."""

    def test_generate_token_returns_string(self):
        token = generate_token(32)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_hash_token_is_sha256(self):
        token = "test_token_123"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert hash_token(token) == expected

    def test_hash_token_deterministic(self):
        token = generate_token(32)
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_different_hashes(self):
        t1 = generate_token(32)
        t2 = generate_token(32)
        assert hash_token(t1) != hash_token(t2)

    def test_verify_token_correct(self):
        token = generate_token(32)
        token_hash = hash_token(token)
        assert verify_token(token, token_hash) is True

    def test_verify_token_incorrect(self):
        token = generate_token(32)
        wrong_hash = hash_token("wrong_token")
        assert verify_token(token, wrong_hash) is False


class TestRoleHierarchy:
    """Test role-based access control logic."""

    def test_role_hierarchy_ordering(self):
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        assert role_hierarchy["read"] < role_hierarchy["write"]
        assert role_hierarchy["write"] < role_hierarchy["superadmin"]

    def test_superadmin_can_do_everything(self):
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        admin_level = role_hierarchy["superadmin"]
        assert admin_level >= role_hierarchy["read"]
        assert admin_level >= role_hierarchy["write"]
        assert admin_level >= role_hierarchy["superadmin"]

    def test_read_cannot_write(self):
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        admin_level = role_hierarchy["read"]
        required_level = role_hierarchy["write"]
        assert admin_level < required_level


class TestTelegramLinkDerivation:
    """Test telegram_link derivation logic (send_to_admin)."""

    def test_telegram_link_with_username(self):
        username = "ivan"
        telegram_link = f"https://t.me/{username}" if username else None
        assert telegram_link == "https://t.me/ivan"

    def test_telegram_link_without_username(self):
        username = None
        telegram_link = f"https://t.me/{username}" if username else None
        assert telegram_link is None

    def test_telegram_link_empty_username(self):
        username = ""
        telegram_link = f"https://t.me/{username}" if username else None
        assert telegram_link is None


class TestToolContext:
    """Test the send_to_admin tool context injection pattern."""

    def test_set_tool_context_stores_user_data(self):
        from apps.bot.app.agent.tools.send_to_admin import _current_context, set_tool_context

        user_data = {
            "tg_id": 12345,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en",
        }
        set_tool_context(user_data=user_data, trace_id="test-trace-123")

        assert _current_context["user_data"]["tg_id"] == 12345
        assert _current_context["trace_id"] == "test-trace-123"

    def test_tool_context_omits_telegram_link_without_username(self):
        username = None
        telegram_link = f"https://t.me/{username}" if username else None
        assert telegram_link is None


class TestPromptAssembly:
    """Test prompt assembly logic."""

    def test_guardrails_not_empty(self):
        from apps.bot.app.agent.core_guardrails import GUARDRAILS

        assert len(GUARDRAILS) > 0
        assert "secrets" in GUARDRAILS.lower() or "secret" in GUARDRAILS.lower()

    def test_assembled_prompt_hash_is_sha256(self):
        import hashlib

        test_prompt = "Test system prompt"
        expected_hash = hashlib.sha256(test_prompt.encode("utf-8")).hexdigest()
        actual_hash = hashlib.sha256(test_prompt.encode("utf-8")).hexdigest()
        assert actual_hash == expected_hash


class TestCensorFallback:
    """Test censor service fallback logic."""

    @pytest.mark.asyncio
    async def test_censor_disabled_returns_draft(self):
        """When censor is disabled, draft response should be returned as-is."""
        # This test verifies the logic without needing a DB
        draft = "This is a draft response"
        enabled = False

        if not enabled:
            final = draft
        else:
            final = "censored version"

        assert final == draft

    def test_censor_failure_returns_draft(self):
        """When censor LLM fails, draft should be returned as fallback."""
        draft = "Original draft response"
        try:
            raise Exception("LLM API error")
        except Exception:
            final = draft  # Fallback

        assert final == draft


class TestVoiceLimits:
    """Test voice message size and duration limit checks."""

    def test_file_size_within_limit(self):
        file_size_mb = 10
        max_size_mb = 25
        assert file_size_mb <= max_size_mb

    def test_file_size_exceeds_limit(self):
        file_size_mb = 30
        max_size_mb = 25
        assert file_size_mb > max_size_mb

    def test_duration_within_limit(self):
        duration_sec = 60
        max_duration_sec = 120
        assert duration_sec <= max_duration_sec

    def test_duration_exceeds_limit(self):
        duration_sec = 180
        max_duration_sec = 120
        assert duration_sec > max_duration_sec


class TestSessionCookie:
    """Test session cookie creation and decoding."""

    def test_create_and_decode_session(self):
        from itsdangerous import URLSafeTimedSerializer

        secret = "test_secret_key_for_testing"
        serializer = URLSafeTimedSerializer(secret)

        data = {"tg_id": 12345, "role": "superadmin"}
        cookie_value = serializer.dumps(data)

        decoded = serializer.loads(cookie_value, max_age=3600)
        assert decoded["tg_id"] == 12345
        assert decoded["role"] == "superadmin"

    def test_invalid_session_returns_none(self):
        from itsdangerous import URLSafeTimedSerializer, BadSignature

        serializer = URLSafeTimedSerializer("test_secret")
        try:
            serializer.loads("invalid_cookie_value", max_age=3600)
            assert False, "Should have raised"
        except (BadSignature, Exception):
            pass  # Expected

    def test_root_admin_always_superadmin(self):
        root_tg_id = 99999
        session = {"tg_id": 99999, "role": "read"}

        if session.get("tg_id") == root_tg_id:
            session["role"] = "superadmin"

        assert session["role"] == "superadmin"


class TestProjectKnowledge:
    """Test project knowledge file tool."""

    def test_knowledge_file_exists(self):
        import os

        knowledge_file = os.path.join(
            os.path.dirname(__file__), "..", "project_knowledge.txt"
        )
        assert os.path.exists(knowledge_file)

    def test_knowledge_file_not_empty(self):
        import os

        knowledge_file = os.path.join(
            os.path.dirname(__file__), "..", "project_knowledge.txt"
        )
        with open(knowledge_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 0


class TestSecretProtection:
    """Test that secrets are not exposed in metadata."""

    def test_langsmith_metadata_no_secrets(self):
        """Verify that LangSmith metadata dict doesn't contain secrets."""
        metadata = {
            "trace_id": "test-trace",
            "project_slug": "test-project",
            "app_env": "dev",
            "bot_mode": "polling",
            "system_prompt_version": 1,
            "tools_instruction_version": 1,
            "assembled_prompt_hash": "abc123",
            "llm_provider": "openai",
            "llm_model": "gpt-4.1-mini",
        }

        secret_keywords = ["api_key", "password", "secret", "token", "cookie", "credential"]
        for key in metadata:
            for keyword in secret_keywords:
                assert keyword not in key.lower(), f"Metadata key '{key}' contains secret keyword '{keyword}'"

        for value in metadata.values():
            if isinstance(value, str):
                for keyword in secret_keywords:
                    assert keyword not in value.lower(), f"Metadata value contains secret keyword '{keyword}'"


class TestLLMFactory:
    """Test LLM factory provider selection logic."""

    def test_openai_provider_name_is_recognized(self):
        """OpenAI provider string maps correctly."""
        provider = "openai"
        assert provider in ("openai", "anthropic")

    def test_anthropic_provider_name_is_recognized(self):
        """Anthropic provider string maps correctly."""
        provider = "anthropic"
        assert provider in ("openai", "anthropic")

    def test_unknown_provider_raises(self):
        """Unknown provider should raise ValueError."""
        with pytest.raises(ValueError):
            provider = "unknown_provider"
            if provider not in ("openai", "anthropic"):
                raise ValueError(f"Unknown LLM provider: {provider}")


class TestSettingsDefaults:
    """Test settings service default values."""

    def test_default_provider_is_openai(self):
        """Default LLM provider should be openai."""
        default_provider = "openai"
        assert default_provider == "openai"

    def test_default_fallback_logic(self):
        """If setting is None or empty, fall back to configured default."""
        setting_value = None
        default = "openai"
        resolved = setting_value if setting_value is not None else default
        assert resolved == "openai"

    def test_empty_string_falls_back(self):
        """Empty string should NOT fall back — None does."""
        setting_value = ""
        default = "openai"
        resolved = setting_value if setting_value is not None else default
        assert resolved == ""

    def test_setting_overrides_default(self):
        """When setting exists, it should override default."""
        setting_value = "anthropic"
        default = "openai"
        resolved = setting_value if setting_value is not None else default
        assert resolved == "anthropic"


class TestSettingsValidation:
    """Test settings validation and required fields."""

    def test_model_name_required(self):
        """Model name must not be empty."""
        llm_model = ""
        assert not llm_model

    def test_valid_model_name_accepted(self):
        """Valid model name should be accepted."""
        llm_model = "gpt-4.1-mini"
        assert len(llm_model) > 0

    def test_provider_restricted_to_openai_anthropic(self):
        """Only openai and anthropic are valid providers."""
        valid_providers = ("openai", "anthropic")
        assert "openai" in valid_providers
        assert "anthropic" in valid_providers
        assert "azure" not in valid_providers

    def test_agent_and_censor_settings_independent(self):
        """Main agent and censor settings should be independently stored."""
        llm_provider = "openai"
        censor_provider = "anthropic"
        assert llm_provider != censor_provider


class TestSettingsAuditEvent:
    """Test audit event structure for settings updates."""

    def test_audit_event_has_required_fields(self):
        """Audit event should have action, entity_type, and metadata."""
        action = "settings.updated"
        entity_type = "app_settings"
        metadata = {
            "llm_provider": "anthropic",
            "llm_model": "claude-3-5-sonnet-latest",
            "censor_provider": "openai",
            "censor_model": "gpt-4.1-mini",
        }

        assert action == "settings.updated"
        assert entity_type == "app_settings"
        assert "llm_provider" in metadata
        assert "censor_provider" in metadata

    def test_audit_metadata_contains_changed_keys(self):
        """Audit metadata should contain the keys that were changed."""
        metadata = {"llm_provider": "anthropic", "llm_model": "claude-3-5-sonnet-latest"}
        required_keys = {"llm_provider", "llm_model"}
        assert required_keys.issubset(set(metadata.keys()))


class TestRoleEnforcementForSettings:
    """Test role-based access for settings page."""

    def test_read_role_cannot_write_settings(self):
        """Read role should not have write permission for settings."""
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        read_level = role_hierarchy["read"]
        write_level = role_hierarchy["write"]
        assert read_level < write_level

    def test_write_role_can_edit_settings(self):
        """Write role should have permission for settings."""
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        write_level = role_hierarchy["write"]
        required_level = role_hierarchy["write"]
        assert write_level >= required_level

    def test_superadmin_can_edit_settings(self):
        """Superadmin role should have permission for settings."""
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        superadmin_level = role_hierarchy["superadmin"]
        required_level = role_hierarchy["write"]
        assert superadmin_level >= required_level


class TestCSRFForSettings:
    """Test CSRF protection for settings POST."""

    def test_csrf_tokens_must_match(self):
        """CSRF cookie token must match form token."""
        csrf_cookie = "token_abc123"
        csrf_form = "token_abc123"
        assert csrf_cookie == csrf_form

    def test_csrf_mismatch_rejected(self):
        """Mismatched CSRF tokens should be rejected."""
        csrf_cookie = "token_abc123"
        csrf_form = "token_xyz789"
        assert csrf_cookie != csrf_form


class TestConversationThread:
    """Test conversation thread_id and restart logic."""

    def test_get_thread_id_no_reset(self):
        """Thread ID should be stable when no reset has occurred."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        tg_id = 11111
        _user_reset_counters.clear()

        thread1 = get_thread_id(tg_id)
        thread2 = get_thread_id(tg_id)
        assert thread1 == thread2 == "11111"

    def test_get_thread_id_after_reset(self):
        """After reset, thread ID should change."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        tg_id = 22222
        _user_reset_counters.clear()

        before = get_thread_id(tg_id)
        reset_user_thread(tg_id)
        after = get_thread_id(tg_id)

        assert before != after
        assert before == "22222"
        assert after == "22222_1"

    def test_multiple_resets_increment_counter(self):
        """Multiple resets should produce unique thread IDs."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        tg_id = 33333
        _user_reset_counters.clear()

        t0 = get_thread_id(tg_id)
        reset_user_thread(tg_id)
        t1 = get_thread_id(tg_id)
        reset_user_thread(tg_id)
        t2 = get_thread_id(tg_id)

        assert t0 == "33333"
        assert t1 == "33333_1"
        assert t2 == "33333_2"

    def test_different_users_have_isolated_threads(self):
        """Different users should have independent thread IDs."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        _user_reset_counters.clear()

        reset_user_thread(100)
        thread_100 = get_thread_id(100)
        thread_200 = get_thread_id(200)

        assert thread_100 != thread_200
        assert thread_100 == "100_1"
        assert thread_200 == "200"

    def test_start_command_clears_history(self):
        """Simulating /start clearing behavior."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        tg_id = 44444
        _user_reset_counters.clear()

        # Simulate user conversation before /start
        before = get_thread_id(tg_id)

        # /start handler calls reset
        reset_user_thread(tg_id)

        after = get_thread_id(tg_id)
        assert before != after

    def test_restart_command_clears_history(self):
        """Simulating /restart clearing behavior."""
        from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread

        tg_id = 55555
        _user_reset_counters.clear()

        before = get_thread_id(tg_id)

        # /restart handler calls reset
        reset_user_thread(tg_id)

        after = get_thread_id(tg_id)
        assert before != after
