import streamlit as st
import google.generativeai as genai
import re
import os
import tempfile
from sqlalchemy import create_engine, text, bindparam
from pypdf import PdfReader


# ==========================================================
# 0. DATABASE 설정 및 연동
# ==========================================================

def read_secret(name, default=""):
    """Secrets가 설정되지 않은 환경에서도 안전하게 읽기"""
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)


DATABASE_URL = read_secret("DATABASE_URL", "")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )


@st.cache_resource
def get_db_engine():
    if not DATABASE_URL:
        st.error(
            "⚠️ Secrets에 DATABASE_URL이 설정되어 있지 않습니다."
        )
        return None

    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 10
            }
        )

        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS history (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            conn.execute(text("""
                ALTER TABLE history
                ADD COLUMN IF NOT EXISTS product_name TEXT;
            """))

            conn.commit()

        return engine

    except Exception as e:
        st.error("❌ DB 연결 실패: {}".format(e))
        return None


engine = get_db_engine()


def load_history_from_db():
    if not engine:
        return []

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, product_name, content
                FROM history
                ORDER BY id DESC;
            """))

            return [
                {
                    "id": row[0],
                    "product_name": row[1],
                    "content": row[2]
                }
                for row in result.fetchall()
            ]

    except Exception as e:
        st.error(
            "DB 데이터 불러오기 오류: {}".format(e)
        )
        return []


def save_history_to_db(product_name,
