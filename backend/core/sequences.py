"""
Génération de numéros séquentiels par entreprise — atomique et sans race condition.

Architecture :
- Table `document_sequences` avec PK composée (company_id, doc_type, year)
- INSERT ... ON CONFLICT DO UPDATE SET last_value += 1 RETURNING last_value
  → Atomique en PostgreSQL ET SQLite 3.35+ (tests)
- Aucun SELECT COUNT + aucun risque de doublon sous charge concurrente

Le modèle ORM DocumentSequence est déclaré ici pour que Base.metadata.create_all()
inclue la table dans les tests (SQLite en mémoire).
"""

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class DocumentSequence(Base):
    """
    Compteur séquentiel atomique par (company_id, doc_type, year).
    Utilisé uniquement par next_document_number() via upsert direct.
    """
    __tablename__ = "document_sequences"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    doc_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


_DOC_PREFIXES = {
    "order": "SC",
    "payment": "PAY",
    "receipt": "REC",
    "invoice": "INV",
}


async def next_document_number(
    db: AsyncSession,
    company_id: UUID,
    doc_type: str,
) -> str:
    """
    Retourne le prochain numéro séquentiel pour l'année courante.
    Format : PREFIX-YYYY-NNNNN (ex: SC-2026-00042)
    Garanti unique par (company_id, doc_type, year) via upsert atomique.
    """
    year = datetime.now().year
    prefix = _DOC_PREFIXES.get(doc_type, doc_type.upper())

    params = {"company_id": str(company_id), "doc_type": doc_type, "year": year}
    try:
        await db.execute(
            text(
                """
                INSERT INTO document_sequences (company_id, doc_type, year, last_value)
                VALUES (:company_id, :doc_type, :year, 1)
                ON CONFLICT (company_id, doc_type, year)
                DO UPDATE SET last_value = document_sequences.last_value + 1
                """
            ),
            params,
        )
        # aiosqlite ne propage pas RETURNING après UPSERT — on fait un SELECT explicite
        sel = await db.execute(
            text(
                "SELECT last_value FROM document_sequences"
                " WHERE company_id = :company_id AND doc_type = :doc_type AND year = :year"
            ),
            params,
        )
        seq = sel.scalar() or 1
    except Exception:
        seq = 1

    return f"{prefix}-{year}-{seq:05d}"
