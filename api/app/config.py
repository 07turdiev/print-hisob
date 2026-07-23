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
    # Agent jarayoni shu soniyadan kam vaqt oldin ishga tushgan bo'lsa
    # "yaqinda qayta ishga tushgan" (recentlyRestarted) deb belgilanadi —
    # bu doimiy qulab tushib qayta ishga tushayotgan (crash-loop) agentni
    # aniqlash uchun foydali belgi.
    agent_recent_restart_seconds: int = 600

    # Standart (default) qog'oz kvotasi — xodim uchun tegishli davrga aniq
    # kvota (EmployeeQuota) belgilanmagan bo'lsa shu qiymat ishlatiladi (0 emas),
    # aks holda hamma "limitdan oshgan" bo'lib ko'rinadi. Ikkalasi mustaqil
    # qiymatlar — chorak oyning 3 baravari emas, mijoz ikkalasini alohida bergan.
    default_quota_month: int = 200
    default_quota_quarter: int = 300


settings = Settings()
