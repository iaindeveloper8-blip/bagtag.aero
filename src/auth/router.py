from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.exceptions import InvalidCredentials, UserAlreadyExists
from src.auth.schemas import UserCreate
from src.database import get_db

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "/dashboard",
    error: str | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"next": next, "error": error},
    )


@router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/dashboard",
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    try:
        user = await auth_service.authenticate_user(db, username, password)
        token = auth_service.create_access_token(user.id)
        redirect_to = unquote(next) if next else "/dashboard"
        if not redirect_to.startswith("/"):
            redirect_to = "/"
        response = RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
        return response
    except InvalidCredentials:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "next": next,
                "error": "Invalid username or password.",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"error": error},
    )


@router.post("/register")
async def register(
    request: Request,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    if password != password_confirm:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Passwords do not match.", "username": username, "email": email},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        data = UserCreate(username=username, email=email, password=password)
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": str(exc), "username": username, "email": email},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        await auth_service.create_user(db, data)
    except UserAlreadyExists:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={
                "error": "Username or email already registered.",
                "username": username,
                "email": email,
            },
            status_code=status.HTTP_409_CONFLICT,
        )
    return RedirectResponse(
        url="/auth/login?success=Account+created.+Please+log+in.",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response
