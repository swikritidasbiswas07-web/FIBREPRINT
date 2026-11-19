"""Local MVP authentication, SQLite accounts and hashed expiring bearer sessions.
For the production deployment add TLS, rate limits, email verification, reset flow, and hardened session transport.
"""
import os
import re
import hmac
import time
import hashlib
import secrets
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

DEFAULT_DB=Path(__file__).resolve().parents[1] / "data" / "fibreprint_users.sqlite3"
SCHEME=HTTPBearer(auto_error=False)
SESSION_SECONDS=60*60*12
ITERATIONS=260000

@contextmanager
def db():
    location=Path(os.getenv('FIBREPRINT_DB_PATH',str(DEFAULT_DB)))
    location.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(location,timeout=15)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript("""CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      expires_at INTEGER NOT NULL);
      CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);""")
    try:
        yield conn
        conn.commit()
    finally:conn.close()

def digest(password: str) -> str:
    salt=secrets.token_bytes(16)
    hashed=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${hashed.hex()}'

def valid_password(password: str, stored: str) -> bool:
    try:
        method, rounds, salt, expected = stored.split('$')
        if method != 'pbkdf2_sha256' or int(rounds)>1000000:return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds))
        return hmac.compare_digest(actual,bytes.fromhex(expected))
    except (ValueError, TypeError):return False

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

def public_user(user):return {'id':user['id'],'name':user['name'],'email':user['email']}

def create_session(conn,user):
    token=secrets.token_urlsafe(36)
    now=int(time.time())
    conn.execute('DELETE FROM sessions WHERE expires_at < ?', (now,))
    conn.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                 (token_hash(token),user['id'],now+SESSION_SECONDS))
    return {'access_token':token,'token_type':'bearer','expires_in':SESSION_SECONDS,'user':public_user(user)}

class RegisterRequest(BaseModel):
    name: str=Field(min_length=2,max_length=80)
    email: str=Field(min_length=5,max_length=254)
    password: str=Field(min_length=10,max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

def normalized_email(email):
    email=email.strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):
        raise HTTPException(422,'Enter a valid email address.')
    return email

def register(payload):
    email=normalized_email(payload.email)
    name=payload.name.strip()
    if len(name)<2:raise HTTPException(422,'Enter your full name.')
    with db() as conn:
        if conn.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
            raise HTTPException(409,'An account with this email already exists.')
        cursor=conn.execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',
              (name,email,digest(payload.password),int(time.time())))
        user=conn.execute('SELECT * FROM users WHERE id=?',(cursor.lastrowid,)).fetchone()
        return create_session(conn,user)

def login(payload):
    email=normalized_email(payload.email)
    with db() as conn:
        user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if not user or not valid_password(payload.password,user['password_hash']):
            raise HTTPException(401,'Incorrect email or password.')
        return create_session(conn,user)

def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(SCHEME)):
    if credentials is None or credentials.scheme.lower()!='bearer':
        raise HTTPException(401,'Please sign in to continue.',headers={'WWW-Authenticate':'Bearer'})
    with db() as conn:
        record=conn.execute("""SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id
            WHERE sessions.token_hash=? AND sessions.expires_at>?""",
            (token_hash(credentials.credentials),int(time.time()))).fetchone()
        if not record:raise HTTPException(401,'Session expired. Please sign in again.')
        return public_user(record)

def logout(credentials:HTTPAuthorizationCredentials|None=Depends(SCHEME)):
    if credentials:
        with db() as conn:conn.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash(credentials.credentials),))
    return {'ok':True}
