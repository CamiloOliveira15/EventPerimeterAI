from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from src.core.database import get_db
from src.domain import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Event])
async def read_events(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.Event).offset(skip).limit(limit))
    events = result.scalars().all()
    return events

@router.post("/", response_model=schemas.Event)
async def create_event(
    event: schemas.EventCreate,
    db: AsyncSession = Depends(get_db)
):
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event
