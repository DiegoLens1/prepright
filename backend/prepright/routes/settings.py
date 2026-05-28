from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    settings = {}
    for s in db.query(models.Setting).all():
        settings[s.key] = s.value
    return settings


@router.put("/{key}")
def update_setting(key: str, val: schemas.SettingUpdate, db: Session = Depends(get_db)):
    db_setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if db_setting:
        db_setting.value = val.value
    else:
        db_setting = models.Setting(key=key, value=val.value)
        db.add(db_setting)
    db.commit()
    return {"key": key, "value": val.value}
