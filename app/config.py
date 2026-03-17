from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Claude API
    anthropic_api_key: str = ""

    # Deepgram (Speech-to-Text)
    deepgram_api_key: str = ""

    # ElevenLabs (Text-to-Speech)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # SendGrid (Email)
    sendgrid_api_key: str = ""

    # Database
    database_url: str = "postgresql://localhost/voiceagent"

    # App Settings
    claude_model: str = "claude-sonnet-4-20250514"
    session_timeout_minutes: int = 30
    log_level: str = "INFO"
    practice_id: str = "default"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
