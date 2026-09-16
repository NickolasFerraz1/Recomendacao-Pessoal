from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, Integer, JSON, String, Text

from app.database import Base


class AnimePerfil(Base):
    __tablename__ = "animes_perfil"

    id = Column(Integer, primary_key=True)
    anilist_id = Column(Integer, unique=True, nullable=False)
    titulo = Column(String, nullable=False)
    status = Column(
        Enum("assistido", "assistindo", "dropado", "quero_assistir", name="status_enum"),
        nullable=False,
    )
    nota = Column(Integer, nullable=True)
    tags_anilist = Column(JSON)
    tags_proprias = Column(JSON)
    sinopse = Column(Text, nullable=True)
    embedding = Column(JSON, nullable=True)
    data_registro = Column(DateTime, default=datetime.utcnow)


class AnimeCatalogo(Base):
    __tablename__ = "animes_catalogo"

    id = Column(Integer, primary_key=True)
    anilist_id = Column(Integer, unique=True, nullable=False)
    titulo = Column(String, nullable=False)
    sinopse = Column(Text, nullable=True)
    tags_anilist = Column(JSON)
    embedding = Column(JSON, nullable=True)
    popularidade = Column(Integer, nullable=True)
    nota_media = Column(Float, nullable=True)
    formato = Column(String, nullable=True)
    ano = Column(Integer, nullable=True)
    data_adicionado = Column(DateTime, default=datetime.utcnow)
