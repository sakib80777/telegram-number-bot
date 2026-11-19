import aiosqlite
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0.0,
                otp_count INTEGER DEFAULT 0,
                referred_by INTEGER,
                is_banned INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT,
                service TEXT,
                phone_number TEXT UNIQUE,
                is_used INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        default_settings = {
            "welcome_msg": "👋 স্বাগতম আমাদের প্রিমিয়াম নাম্বার বটে!\n\nনিচের মেনু থেকে আপনার পছন্দের দেশের নাম্বার সংগ্রহ করুন।",
            "otp_rate": "5.0",
            "min_withdraw": "50.0",
            "refer_bonus": "2.0",
            "api_key": "",
            "api_url": "",
            "theme_style": "PREMIUM"
        }
        for k, v in default_settings.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        await db.commit()

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""

async def update_setting(key: str, value: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def add_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            if await cursor.fetchone() is None:
                await db.execute(
                    "INSERT INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
                    (user_id, username, full_name, referred_by)
                )
                if referred_by:
                    bonus = float(await get_setting("refer_bonus"))
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus, referred_by))
                await db.commit()
                return True
        return False
