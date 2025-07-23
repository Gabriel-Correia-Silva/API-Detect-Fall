import uvicorn
import csv
import sqlite3
import os
import hashlib
import hmac
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models import DetailedHealthAndSensorPayload
from typing import List, Dict
import json
import threading

# --- CONFIGURAÇÃO ---
DB_FILE = "health_data.db"
CSV_DIR = "csv_data"

# Chave secreta para gerar hashes consistentes dos userIds
# IMPORTANTE: Altere esta chave em produção e mantenha-a secreta!
SECRET_KEY = "sua-chave-secreta-super-forte-aqui-2024"

# Criar um Lock global para controlar o acesso aos ficheiros
db_lock = threading.Lock()

app = FastAPI(
    title="API de Monitoramento de Saúde",
    description="Recebe, processa e armazena dados de saúde e sensores com privacidade protegida.",
    version="1.5.0"  # Versão com anonimização
)

# --- FUNÇÕES DE PRIVACIDADE ---
def anonymize_user_id(original_user_id: str) -> str:
    """
    Gera um ID de usuário anônimo mas consistente usando HMAC-SHA256.
    O mesmo userId original sempre gerará o mesmo hash anônimo.
    """
    # Usa HMAC para gerar um hash seguro e consistente
    anonymous_id = hmac.new(
        SECRET_KEY.encode('utf-8'), 
        original_user_id.encode('utf-8'), 
        hashlib.sha256
    ).hexdigest()[:16]  # Usa apenas os primeiros 16 caracteres para um ID mais compacto
    
    return f"anon_{anonymous_id}"

def anonymize_payload(payload: DetailedHealthAndSensorPayload) -> DetailedHealthAndSensorPayload:
    """
    Cria uma cópia do payload com todos os userIds anonimizados.
    """
    anonymous_user_id = anonymize_user_id(payload.userId)
    
    # Criar uma cópia do payload com o userId anonimizado
    payload_dict = payload.model_dump()
    payload_dict['userId'] = anonymous_user_id
    
    # Anonimizar userIds em heart rate records
    for record in payload_dict['heartRateRecords']:
        record['userId'] = anonymous_user_id
    
    # Anonimizar userIds em sleep sessions
    for session in payload_dict['sleepSessions']:
        session['sessionSummary']['userId'] = anonymous_user_id
    
    # Anonimizar userIds em calorie records
    for calorie in payload_dict['calorieRecords']:
        calorie['userId'] = anonymous_user_id
    
    # Anonimizar userIds em oxygen saturation records
    for oxygen in payload_dict['oxygenSaturationRecords']:
        oxygen['userId'] = anonymous_user_id
    
    # Recriar o payload com dados anonimizados
    return DetailedHealthAndSensorPayload(**payload_dict)

# --- FUNÇÕES DA BASE DE DADOS (SQLITE) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabelas existentes
    cursor.execute("""CREATE TABLE IF NOT EXISTS heart_rate (
        userId TEXT, 
        requestTimestamp INTEGER, 
        timestamp INTEGER, 
        bpm INTEGER, 
        PRIMARY KEY (userId, timestamp)
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS accelerometer (
        userId TEXT, 
        requestTimestamp INTEGER, 
        timestamp INTEGER, 
        x REAL, 
        y REAL, 
        z REAL
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS gyroscope (
        userId TEXT, 
        requestTimestamp INTEGER, 
        timestamp INTEGER, 
        x REAL, 
        y REAL, 
        z REAL
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS steps (
        userId TEXT, 
        requestTimestamp INTEGER, 
        date TEXT, 
        hour INTEGER, 
        count INTEGER, 
        PRIMARY KEY (userId, date, hour)
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS sleep_sessions (
        userId TEXT, 
        requestTimestamp INTEGER, 
        sessionId TEXT PRIMARY KEY, 
        startTime TEXT, 
        endTime TEXT, 
        durationMinutes INTEGER
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS sleep_stages (
        stageId INTEGER PRIMARY KEY AUTOINCREMENT, 
        sessionId TEXT, 
        type INTEGER, 
        startTime TEXT, 
        endTime TEXT, 
        FOREIGN KEY (sessionId) REFERENCES sleep_sessions(sessionId)
    )""")
    
    # Novas tabelas para calorias e oxigenação
    cursor.execute("""CREATE TABLE IF NOT EXISTS calories (
        userId TEXT, 
        requestTimestamp INTEGER, 
        healthConnectId TEXT, 
        startTime TEXT, 
        endTime TEXT, 
        kilocalorias REAL, 
        tipo TEXT,
        PRIMARY KEY (userId, healthConnectId)
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS oxygen_saturation (
        userId TEXT, 
        requestTimestamp INTEGER, 
        timestamp INTEGER, 
        spo2 REAL,
        PRIMARY KEY (userId, timestamp)
    )""")
    
    conn.commit()
    conn.close()
    print(f"Base de dados '{DB_FILE}' inicializada com sucesso.")

def save_to_sql(payload: DetailedHealthAndSensorPayload):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Heart Rate Records
        for record in payload.heartRateRecords:
            cursor.execute("""INSERT OR IGNORE INTO heart_rate VALUES (?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, record.timestamp, record.bpm))
        
        # Accelerometer Readings
        for reading in payload.accelerometerReadings:
            cursor.execute("""INSERT INTO accelerometer VALUES (?, ?, ?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, reading.timestamp, 
                          reading.x, reading.y, reading.z))
        
        # Gyroscope Readings
        for reading in payload.gyroscopeReadings:
            cursor.execute("""INSERT INTO gyroscope VALUES (?, ?, ?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, reading.timestamp, 
                          reading.x, reading.y, reading.z))
        
        # Steps Data
        for hour, count in payload.steps.hourlyCounts.items():
            cursor.execute("""INSERT OR IGNORE INTO steps VALUES (?, ?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, payload.steps.date, hour, count))
        
        # Sleep Sessions
        for session in payload.sleepSessions:
            summary = session.sessionSummary
            # Handle optional endTime and durationMinutes fields
            end_time = getattr(summary, 'endTime', None)
            duration_minutes = getattr(summary, 'durationMinutes', None)
            
            cursor.execute("""INSERT OR IGNORE INTO sleep_sessions VALUES (?, ?, ?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, summary.healthConnectId, 
                          summary.startTime, end_time, duration_minutes))
            
            # Sleep Stages
            for stage in session.stages:
                cursor.execute("""INSERT INTO sleep_stages (sessionId, type, startTime, endTime) VALUES (?, ?, ?, ?)""", 
                             (stage.sessionId, stage.type, stage.startTime, stage.endTime))
        
        # Calorie Records
        for calorie in payload.calorieRecords:
            cursor.execute("""INSERT OR IGNORE INTO calories VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, calorie.healthConnectId, 
                          calorie.startTime, calorie.endTime, calorie.kilocalorias, calorie.tipo))
        
        # Oxygen Saturation Records
        for oxygen in payload.oxygenSaturationRecords:
            cursor.execute("""INSERT OR IGNORE INTO oxygen_saturation VALUES (?, ?, ?, ?)""", 
                         (payload.userId, payload.timestamp, oxygen.timestamp, oxygen.spo2))
        
        conn.commit()
        print("Dados guardados com sucesso na base de dados SQLite.")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao guardar dados na base de dados: {e}")
        raise
    finally:
        conn.close()

# --- FUNÇÕES DE ARMAZENAMENTO EM CSV ---
def save_to_csv(payload: DetailedHealthAndSensorPayload):
    os.makedirs(CSV_DIR, exist_ok=True)
    
    def append_to_file(filename: str, headers: List[str], data_rows: List[Dict]):
        file_path = os.path.join(CSV_DIR, filename)
        file_exists = os.path.isfile(file_path)
        
        if data_rows:  # Only write if there's data
            with open(file_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(data_rows)
    
    # Heart Rate Data
    hr_data = [{**r.model_dump(), 'userId': payload.userId, 'requestTimestamp': payload.timestamp} 
               for r in payload.heartRateRecords]
    if hr_data:
        append_to_file("heart_rate.csv", list(hr_data[0].keys()), hr_data)
    
    # Accelerometer Data
    accel_data = [{**r.model_dump(), 'userId': payload.userId, 'requestTimestamp': payload.timestamp} 
                  for r in payload.accelerometerReadings]
    if accel_data:
        append_to_file("accelerometer.csv", list(accel_data[0].keys()), accel_data)
    
    # Gyroscope Data
    gyro_data = [{**r.model_dump(), 'userId': payload.userId, 'requestTimestamp': payload.timestamp} 
                 for r in payload.gyroscopeReadings]
    if gyro_data:
        append_to_file("gyroscope.csv", list(gyro_data[0].keys()), gyro_data)
    
    # Steps Data
    steps_data = []
    for hour, count in payload.steps.hourlyCounts.items():
        steps_data.append({
            'userId': payload.userId,
            'requestTimestamp': payload.timestamp,
            'date': payload.steps.date,
            'hour': hour,
            'count': count
        })
    if steps_data:
        append_to_file("steps.csv", ['userId', 'requestTimestamp', 'date', 'hour', 'count'], steps_data)
    
    # Sleep Sessions Data
    sleep_data = []
    for session in payload.sleepSessions:
        summary = session.sessionSummary
        sleep_data.append({
            **summary.model_dump(),
            'requestTimestamp': payload.timestamp
        })
    if sleep_data:
        append_to_file("sleep_sessions.csv", list(sleep_data[0].keys()), sleep_data)
    
    # Sleep Stages Data
    stages_data = []
    for session in payload.sleepSessions:
        for stage in session.stages:
            stages_data.append({
                **stage.model_dump(),
                'userId': payload.userId,
                'requestTimestamp': payload.timestamp
            })
    if stages_data:
        append_to_file("sleep_stages.csv", list(stages_data[0].keys()), stages_data)
    
    # Calorie Data
    cal_data = [{**c.model_dump(), 'requestTimestamp': payload.timestamp} 
                for c in payload.calorieRecords]
    if cal_data:
        append_to_file("calories.csv", list(cal_data[0].keys()), cal_data)
    
    # Oxygen Saturation Data
    oxygen_data = [{**o.model_dump(), 'requestTimestamp': payload.timestamp} 
                   for o in payload.oxygenSaturationRecords]
    if oxygen_data:
        append_to_file("oxygen_saturation.csv", list(oxygen_data[0].keys()), oxygen_data)
    
    print(f"Dados guardados com sucesso no diretório '{CSV_DIR}'.")

# --- ENDPOINTS DA API ---
@app.on_event("startup")
async def startup_event():
    init_db()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation Error",
            "errors": error_details
        }
    )

@app.get("/")
def read_root():
    return {"status": "API de Monitoramento de Saúde está operacional!", "privacy": "UserIds são automaticamente anonimizados"}

@app.get("/v1/privacy/test/{user_id}")
def test_anonymization(user_id: str):
    """
    Endpoint de teste para verificar como um userId seria anonimizado.
    Útil para testes durante desenvolvimento.
    """
    anonymous_id = anonymize_user_id(user_id)
    return {
        "original": user_id,
        "anonymous": anonymous_id,
        "note": "O ID original nunca é armazenado na base de dados"
    }

@app.post("/v1/data/detailed")
def upload_detailed_health_data(payload: DetailedHealthAndSensorPayload):
    with db_lock:
        try:
            original_user_id = payload.userId
            
            # Anonimizar o payload antes de processar
            anonymous_payload = anonymize_payload(payload)
            anonymous_user_id = anonymous_payload.userId
            
            print(f"--- Dados Recebidos ---")
            print(f"ID Original (não armazenado): {original_user_id}")
            print(f"ID Anônimo: {anonymous_user_id}")
            print(f"Heart Rate Records: {len(anonymous_payload.heartRateRecords)}")
            print(f"Sleep Sessions: {len(anonymous_payload.sleepSessions)}")
            print(f"Calorie Records: {len(anonymous_payload.calorieRecords)}")
            print(f"Oxygen Records: {len(anonymous_payload.oxygenSaturationRecords)}")
            print(f"Accelerometer Readings: {len(anonymous_payload.accelerometerReadings)}")
            print(f"Gyroscope Readings: {len(anonymous_payload.gyroscopeReadings)}")
            
            # Armazenar dados anonimizados
            save_to_sql(anonymous_payload)
            save_to_csv(anonymous_payload)
            
            print("--- Processamento Concluído com Sucesso ---")
            return {
                "status": "sucesso", 
                "message": "Dados recebidos e guardados com sucesso (anonimizados).",
                "anonymousUserId": anonymous_user_id  # Retorna o ID anônimo para referência
            }
            
        except Exception as e:
            print(f"Erro ao processar o payload: {e}")
            raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)