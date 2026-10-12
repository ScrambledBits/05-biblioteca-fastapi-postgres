import os
import socket
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import db

Conexion = Annotated[psycopg.Connection, Depends(db.obtener_conexion)]


class LibroNuevo(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=120)
    anio: int | None = Field(default=None, ge=0, le=2100)


class Libro(LibroNuevo):
    id: int
    prestado: bool


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    db.inicializar()
    yield


app = FastAPI(
    title="Biblioteca",
    description="API educativa para gestionar libros y préstamos.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


def buscar(conexion: psycopg.Connection, libro_id: int) -> dict:
    libro = conexion.execute(
        "SELECT * FROM libros WHERE id = %s", (libro_id,)
    ).fetchone()
    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    return libro


@app.get("/")
def inicio():
    return {
        "app": "biblioteca",
        "entorno": os.environ.get("APP_ENV", "desarrollo"),
        "contenedor": socket.gethostname(),
        "documentacion": "/docs",
    }


@app.get("/health")
def health():
    try:
        with db.conectar() as conexion:
            conexion.execute("SELECT 1")
    except psycopg.OperationalError:
        return JSONResponse(
            {"estado": "error", "postgres": "sin conexion"}, status_code=503
        )
    return {"estado": "ok", "postgres": "conectado"}


@app.get("/libros", response_model=list[Libro])
def listar(conexion: Conexion, disponibles: bool = False):
    consulta = "SELECT * FROM libros"
    if disponibles:
        consulta += " WHERE NOT prestado"
    return conexion.execute(consulta + " ORDER BY id").fetchall()


@app.get("/libros/{libro_id}", response_model=Libro)
def obtener(libro_id: int, conexion: Conexion):
    return buscar(conexion, libro_id)


@app.post("/libros", response_model=Libro, status_code=201)
def crear(libro: LibroNuevo, conexion: Conexion):
    return conexion.execute(
        "INSERT INTO libros (titulo, autor, anio) VALUES (%s, %s, %s) RETURNING *",
        (libro.titulo, libro.autor, libro.anio),
    ).fetchone()


@app.post("/libros/{libro_id}/prestamo", response_model=Libro)
def prestar(libro_id: int, conexion: Conexion):
    if buscar(conexion, libro_id)["prestado"]:
        raise HTTPException(status_code=409, detail="El libro ya está prestado")
    return conexion.execute(
        "UPDATE libros SET prestado = TRUE WHERE id = %s RETURNING *", (libro_id,)
    ).fetchone()


@app.delete("/libros/{libro_id}/prestamo", response_model=Libro)
def devolver(libro_id: int, conexion: Conexion):
    if not buscar(conexion, libro_id)["prestado"]:
        raise HTTPException(status_code=409, detail="El libro no está prestado")
    return conexion.execute(
        "UPDATE libros SET prestado = FALSE WHERE id = %s RETURNING *", (libro_id,)
    ).fetchone()


@app.delete("/libros/{libro_id}", status_code=204)
def borrar(libro_id: int, conexion: Conexion):
    buscar(conexion, libro_id)
    conexion.execute("DELETE FROM libros WHERE id = %s", (libro_id,))
    return Response(status_code=204)
