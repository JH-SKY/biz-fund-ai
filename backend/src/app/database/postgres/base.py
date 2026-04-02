# src/app/database/postgres/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    공통 부모 클래스.
    - 모든 DB 모델이 상속받아야 하는 최상위 설계도.
    - Alembic이 이 클래스를 상속받은 객체들을 추적하여 테이블을 생성한다.
    """

    pass
