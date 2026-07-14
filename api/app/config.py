from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/printer_hisob"
    # Agentlar (.exe) uchun — X-API-Key sarlavhasi (mashina autentifikatsiyasi).
    api_key: str = ""
    auto_create_tables: bool = True
    echo_sql: bool = False

    # Dashboard foydalanuvchisi uchun login/parol (JWT bilan autentifikatsiya).
    auth_username: str = "admin"
    auth_password: str = ""
    # JWT tokenlarni imzolash uchun maxfiy kalit. Bo'sh bo'lsa login ishlamaydi (fail-closed).
    jwt_secret: str = ""
    # Token amal qilish muddati (daqiqalarda). Standart — 12 soat.
    jwt_expire_minutes: int = 720

    # CORS: dashboard qaysi manzil(lar)dan brauzer orqali so'rov yubora oladi.
    # Vergul bilan ajratilgan ro'yxat (masalan "https://hisob.example.uz").
    # Mahalliy dev portlari (istalgan localhost) baribir avtomatik ruxsat etiladi.
    cors_origins: str = ""

    # Agent shu daqiqadan beri signal bermasa, "aloqasi yo'q" (stale) deb
    # belgilanadi (heartbeat oralig'idan kattaroq qiling).
    agent_stale_minutes: int = 60


settings = Settings()
