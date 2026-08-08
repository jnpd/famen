"""重置本地用户密码，不删除 SQLite 中的知识库/参数数据。

用法：
    python reset_admin_password.py --username admin --password NewPassword123!
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User, UserSession


def main():
    parser = argparse.ArgumentParser(description="重置阀门知识库用户密码")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    if len(args.password) < 8:
        raise SystemExit("密码至少 8 位")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username))
        if not user:
            raise SystemExit(f"用户不存在：{args.username}")
        password_hash, password_salt = hash_password(args.password)
        user.password_hash = password_hash
        user.password_salt = password_salt
        for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id)).all():
            db.delete(session)
        db.commit()
    print(f"密码已重置：{args.username}")


if __name__ == "__main__":
    main()
