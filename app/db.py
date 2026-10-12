import os
from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://biblioteca:biblioteca@localhost:5432/biblioteca"
)

LIBROS_INICIALES = [
    ("Cien años de soledad", "Gabriel García Márquez", 1967),
    ("Rayuela", "Julio Cortázar", 1963),
    ("Pedro Páramo", "Juan Rulfo", 1955),
    ("Ficciones", "Jorge Luis Borges", 1944),
]


def conectar() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5)


def obtener_conexion() -> Iterator[psycopg.Connection]:
    with conectar() as conexion:
        yield conexion


def inicializar() -> None:
    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS libros (
                id SERIAL PRIMARY KEY,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL,
                anio INTEGER,
                prestado BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        vacia = (
            conexion.execute("SELECT COUNT(*) AS n FROM libros").fetchone()["n"] == 0
        )
        if vacia:
            with conexion.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO libros (titulo, autor, anio) VALUES (%s, %s, %s)",
                    LIBROS_INICIALES,
                )
