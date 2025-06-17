import sqlite3
from datetime import datetime

DB_FILE = "chats.db"

def conectar():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def crear_tablas():
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            rol TEXT NOT NULL,
            contenido TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id)
        )
    """)
    conn.commit()
    conn.close()

def crear_chat(nombre):
    conn = conectar()
    c = conn.cursor()
    c.execute("INSERT INTO chats (nombre) VALUES (?)", (nombre,))
    conn.commit()
    chat_id = c.lastrowid
    conn.close()
    return chat_id

def obtener_chats():
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM chats ORDER BY creado_en DESC")
    chats = c.fetchall()
    conn.close()
    return chats

def obtener_mensajes(chat_id):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT rol, contenido FROM mensajes WHERE chat_id = ? ORDER BY id", (chat_id,))
    mensajes = [{"role": r, "content": c} for r, c in c.fetchall()]
    conn.close()
    return mensajes

def guardar_mensaje(chat_id, rol, contenido):
    conn = conectar()
    c = conn.cursor()
    c.execute("INSERT INTO mensajes (chat_id, rol, contenido) VALUES (?, ?, ?)", (chat_id, rol, contenido))
    conn.commit()
    conn.close()
