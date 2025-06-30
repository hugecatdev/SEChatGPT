import os
from contextlib import asynccontextmanager
from datetime import datetime

import markdown
import openai
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, delete, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

DATABASE_URL = "sqlite+aiosqlite:///./chat_history.db"

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

openai.api_key = os.getenv("OPENAI_API_KEY")


async def get_phone_number(request: Request) -> str:
    phone_number = request.headers.get("SE-Phone-Number")

    if not phone_number:
        raise HTTPException(
            status_code=400,
            detail="This application only works in SMS Explorer browser"
        )

    return phone_number


async def get_session():
    async with async_session() as session:
        yield session


async def get_or_create_chat_session(phone_number: str, db: AsyncSession):
    result = await db.execute(
        select(ChatSession).where(ChatSession.phone_number == phone_number)
    )

    chat_session = result.scalar_one_or_none()

    if not chat_session:
        chat_session = ChatSession(phone_number=phone_number)
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)

    return chat_session


async def get_chat_history(session_id: int, db: AsyncSession):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    return result.scalars().all()


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request, db: AsyncSession = Depends(get_session)):
    phone_number = await get_phone_number(request)
    chat_session = await get_or_create_chat_session(phone_number, db)
    messages = await get_chat_history(chat_session.id, db)

    for message in messages:
        if message.role == "assistant":
            message.content = markdown.markdown(message.content, extensions=['codehilite', 'fenced_code'])

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "messages": messages
    })


@app.post("/send")
async def send_message(
        request: Request,
        message: str = Form(...),
        db: AsyncSession = Depends(get_session)
):
    phone_number = await get_phone_number(request)
    chat_session = await get_or_create_chat_session(phone_number, db)

    user_message = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=message
    )

    db.add(user_message)
    await db.commit()

    messages = await get_chat_history(chat_session.id, db)
    openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4.1-mini",
            messages=openai_messages
        )

        assistant_content = response.choices[0].message.content

        assistant_message = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=assistant_content
        )
        db.add(assistant_message)
        await db.commit()

    except Exception as e:
        error_message = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=f"Error: {str(e)}"
        )
        db.add(error_message)
        await db.commit()

    return RedirectResponse(url="/", status_code=303)


@app.post("/clear")
async def clear_history(request: Request, db: AsyncSession = Depends(get_session)):
    phone_number = await get_phone_number(request)
    chat_session = await get_or_create_chat_session(phone_number, db)

    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == chat_session.id))
    await db.commit()

    return RedirectResponse(url="/", status_code=303)
