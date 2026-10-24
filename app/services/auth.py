import hashlib
import time

from fastapi import HTTPException
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.security import DUMMY_HASH, create_token, password_hasher
from app.models import LoginRateLimit, User
from app.schemas import Login, Register


async def register(db: AsyncSession, data: Register):
    email = str(data.email).lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email is already registered")
    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=await run_in_threadpool(password_hasher.hash, data.password),
    )
    db.add(user)
    await db.flush()
    return user


async def login(db: AsyncSession, data: Login):
    user = await db.scalar(select(User).where(User.email == str(data.email).lower()))
    try:
        valid = await run_in_threadpool(
            password_hasher.verify, data.password, user.password_hash if user else DUMMY_HASH
        )
    except UnknownHashError:
        valid = False
    if not valid or user is None or not user.is_active:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    return {"access_token": create_token(user.id), "token_type": "bearer"}


async def rate_limit_login(db: AsyncSession, ip: str):
    settings = get_settings()
    key = hashlib.sha256(ip.encode()).hexdigest()
    window_start = int(time.time()) // settings.login_window_seconds * settings.login_window_seconds
    dialect = db.get_bind().dialect.name
    insert = (
        pg_insert if dialect == "postgresql" else sqlite_insert if dialect == "sqlite" else None
    )
    if insert is None:
        raise RuntimeError(f"Login rate limiting does not support database dialect {dialect}")

    statement = insert(LoginRateLimit).values(ip_hash=key, window_start=window_start, attempts=1)
    statement = statement.on_conflict_do_update(
        index_elements=[LoginRateLimit.ip_hash],
        set_={
            "window_start": statement.excluded.window_start,
            "attempts": case(
                (
                    LoginRateLimit.window_start == statement.excluded.window_start,
                    LoginRateLimit.attempts + 1,
                ),
                else_=1,
            ),
        },
    ).returning(LoginRateLimit.attempts)
    count = await db.scalar(statement)
    # Commit separately so failed-login HTTP errors do not roll back the limiter.
    await db.commit()
    if count > settings.login_limit:
        raise HTTPException(
            429,
            "Too many login attempts",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
