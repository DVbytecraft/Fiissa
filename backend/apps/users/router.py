from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.schemas import UserResponse, UserUpdate
from apps.users.service import UserService
from core.database import get_db
from core.dependencies import get_current_user, require_permission

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("/me", response_model=UserResponse, summary="Mon profil")
async def get_my_profile(current_user=Depends(get_current_user)):
    """Retourne le profil complet de l'utilisateur connecté."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.patch("/me", response_model=UserResponse, summary="Modifier mon profil")
async def update_my_profile(
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour les informations du profil de l'utilisateur connecté."""
    service = UserService(db)
    user = await service.update_profile(current_user.id, data.model_dump(exclude_none=True))
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.delete("/me", summary="Supprimer mon compte")
async def delete_my_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Désactive le compte (soft-delete).
    Les données sont conservées pour les audits.
    """
    service = UserService(db)
    await service.deactivate(current_user.id)
    return {"message": "Compte désactivé. Vos données seront supprimées sous 30 jours."}


@router.get("/{user_id}", response_model=UserResponse, summary="Profil d'un utilisateur")
async def get_user(
    user_id: UUID,
    current_user=Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_db),
):
    """Accès réservé super_admin et company_owner."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.patch("/{user_id}/deactivate", summary="Désactiver un utilisateur")
async def deactivate_user(
    user_id: UUID,
    current_user=Depends(require_permission("users.deactivate")),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    await service.deactivate(user_id)
    return {"message": "Utilisateur désactivé"}


@router.patch("/{user_id}/reactivate", summary="Réactiver un utilisateur")
async def reactivate_user(
    user_id: UUID,
    current_user=Depends(require_permission("users.deactivate")),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    await service.reactivate(user_id)
    return {"message": "Utilisateur réactivé"}
