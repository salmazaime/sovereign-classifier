import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.auth.api_keys import generate_api_key
from app.auth.dependencies import AuthenticatedUser, get_current_user, get_postgres_repo_for_auth, require_role
from app.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, hash_password, verify_password
from app.db.repository import PostgresRepository
from app.schemas import (
    ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeySummary,
    InviteUserRequest, RegisterRequest, UserSummary,
)
from app.schemas import CompanyProfileResponse, CompanyUpdateRequest, MeResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES
    roles: list[str] = [] 




@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> TokenResponse:
    user = postgres_repo.get_user_by_email(body.email)

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
    )
    if user is None:
        raise invalid_credentials
    if not verify_password(body.password, user["password_hash"]):
        raise invalid_credentials

    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        logger.error("JWT_SECRET_KEY not set -- cannot issue tokens.")
        raise HTTPException(status_code=500, detail="Server authentication is misconfigured.")

    roles = postgres_repo.get_user_roles(user["id"])
    token = create_access_token(
        subject_user_id=str(user["id"]), company_id=str(user["company_id"]),
        roles=roles, secret_key=secret,
    )
    return TokenResponse(access_token=token, roles=roles)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    body: RegisterRequest,
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> TokenResponse:
    existing = postgres_repo.get_user_by_email(body.admin_email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    company_id = postgres_repo.upsert_company(name=body.company_name, sector=body.company_sector)
    user_id = postgres_repo.create_user_with_role(
        company_id=company_id, name=body.admin_name, email=body.admin_email,
        password_hash=hash_password(body.admin_password), role_name="admin",
    )

    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="Server authentication is misconfigured.")
    token = create_access_token(str(user_id), str(company_id), ["admin"], secret)
    return TokenResponse(access_token=token, roles=["admin"])


@router.post("/users", response_model=UserSummary, status_code=201)
def invite_user(
    body: InviteUserRequest,
    user: AuthenticatedUser = Depends(require_role("admin")),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> UserSummary:
    if postgres_repo.get_user_by_email(body.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    new_user_id = postgres_repo.create_user_with_role(
        company_id=UUID(user.company_id), name=body.name, email=body.email,
        password_hash=hash_password(body.password), role_name=body.role,
    )
    return UserSummary(id=str(new_user_id), name=body.name, email=body.email, roles=[body.role])


@router.get("/users", response_model=list[UserSummary])
def list_users(
    user: AuthenticatedUser = Depends(get_current_user),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> list[UserSummary]:
    rows = postgres_repo.list_company_users(UUID(user.company_id))
    return [UserSummary(id=str(r["id"]), name=r["name"], email=r["email"], roles=r["roles"]) for r in rows]


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=201)
def create_api_key_self_service(
    body: ApiKeyCreateRequest,
    user: AuthenticatedUser = Depends(require_role("admin")),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> ApiKeyCreateResponse:
    plaintext, key_hash = generate_api_key()
    key_id = postgres_repo.create_api_key(
        company_id=UUID(user.company_id), name=body.name, key_hash=key_hash, created_by=UUID(user.user_id),
    )
    return ApiKeyCreateResponse(api_key_id=str(key_id), plaintext_key=plaintext)


@router.get("/api-keys", response_model=list[ApiKeySummary])
def list_api_keys(
    user: AuthenticatedUser = Depends(require_role("admin")),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> list[ApiKeySummary]:
    rows = postgres_repo.list_company_api_keys(UUID(user.company_id))
    return [
        ApiKeySummary(
            id=str(r["id"]), name=r["name"], revoked=r["revoked"],
            created_at=r["created_at"].isoformat(),
            last_used_at=r["last_used_at"].isoformat() if r["last_used_at"] else None,
        ) for r in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
def revoke_api_key(
    api_key_id: UUID,
    user: AuthenticatedUser = Depends(require_role("admin")),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> None:
    revoked = postgres_repo.revoke_api_key(api_key_id, UUID(user.company_id))
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found for this company.")

from app.schemas import CompanyProfileResponse, CompanyUpdateRequest, MeResponse


@router.get("/me", response_model=MeResponse)
def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> MeResponse:
    user_row = postgres_repo.get_user_by_id(UUID(user.user_id))
    company = postgres_repo.get_company_profile(UUID(user.company_id))
    return MeResponse(
        user_id=user.user_id, name=user_row["name"], email=user_row["email"], roles=user.roles,
        company=CompanyProfileResponse(
            id=str(company["id"]), name=company["name"], sector=company["sector"],
            is_oiv=company["is_oiv"], oiv_sector=company["oiv_sector"],
            qualified_provider_required=company["qualified_provider_required"],
        ),
    )


@router.patch("/company", response_model=CompanyProfileResponse)
def update_company(
    body: CompanyUpdateRequest,
    user: AuthenticatedUser = Depends(require_role("admin")),
    postgres_repo: PostgresRepository = Depends(get_postgres_repo_for_auth),
) -> CompanyProfileResponse:
    row = postgres_repo.update_company_profile(
        company_id=UUID(user.company_id), sector=body.sector, is_oiv=body.is_oiv,
        oiv_sector=body.oiv_sector, qualified_provider_required=body.qualified_provider_required,
    )
    return CompanyProfileResponse(
        id=str(row["id"]), name=row["name"], sector=row["sector"], is_oiv=row["is_oiv"],
        oiv_sector=row["oiv_sector"], qualified_provider_required=row["qualified_provider_required"],
    )
    