from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import psycopg2

app = FastAPI(title="GosMonety API")

DB_HOST = "localhost"
DB_NAME = "money" 
DB_USER = "postgres"
DB_PASS = "12321"

def get_conn():
    return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS, options='-c client_encoding=UTF8')

class CoinIn(BaseModel):
    country_id: int
    metal_id: int
    denomination: float
    weight: float
    year: str | None = None
    features: str | None = None

class CollectorIn(BaseModel):
    last_name: str
    first_name: str
    patronomic: str | None = None
    country_id: int
    email: str | None = None

class RecordIn(BaseModel):
    coin_id: int
    collector_id: int
    source_id: int

@app.get("/", response_class=HTMLResponse)
def read_root():
    return FileResponse('index.html')

@app.get("/api/dicts")
def get_dictionaries():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM cns.country")
    countries = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM cns.metal")
    metals = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT id, last_name || ' ' || first_name AS name FROM cns.collectors")
    collectors = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM cns.source")
    sources = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()
    return {"countries": countries, "metals": metals, "collectors": collectors, "sources": sources}

@app.get("/api/available-coins")
def get_available_coins():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cns.v_available_coins")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collectors-data")
def get_collectors_data(country: str = "Все", sort_by: str = "last_name", sort_order: str = "ASC"):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cns.fn_get_filtered_collectors(%s, %s, %s)", 
                    (country, sort_by, sort_order))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/coins-data")
def get_coins_data(country: str = "Все", metal: str = "Все", sort_by: str = "id", sort_order: str = "ASC"):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cns.fn_get_filtered_coins(%s, %s, %s, %s)", 
                    (country, metal, sort_by, sort_order))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/coins")
def get_all_coins():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cns.v_coins_with_owners")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

@app.post("/api/coins")
def add_coin(data: CoinIn):
    try:
        conn = get_conn()
        cur = conn.cursor()
        # ПРИВОДИМ ВСЁ К ТИПАМ БАЗЫ ДАННЫХ!
        cur.execute("""
            CALL cns.sp_add_coin(%s, %s, %s::numeric, %s::numeric, %s::date, %s::text)
        """, (data.country_id, data.metal_id, data.denomination, data.weight, data.year, data.features))
        conn.commit()
        return {"status": "success", "message": "Монета добавлена!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/api/collectors")
def add_collector(data: CollectorIn):
    try:
        conn = get_conn()
        cur = conn.cursor()
        # Тоже добавляем ::text для безопасности
        cur.execute("""
            CALL cns.sp_add_collector(%s::text, %s::text, %s::text, %s, %s::text)
        """, (data.last_name, data.first_name, data.patronomic, data.country_id, data.email))
        conn.commit()
        return {"status": "success", "message": "Коллекционер добавлен!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/api/records")
def give_coin(data: RecordIn):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("CALL cns.sp_give_coin(%s, %s, %s)", 
                    (data.coin_id, data.collector_id, data.source_id))
        conn.commit()
        return {"status": "success", "message": "Монета успешно выдана!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()