# 🏥 API de Monitoramento de quedas

## 🚀 Características

- **Receção Completa**: Batimentos cardíacos, passos, sono, calorias, oxigenação, acelerómetro, giroscópio
- **Armazenamento Duplo**: SQLite (base de dados) + CSV (análise/backup) 
- **Proteção de Privacidade**: Anonimização automática via HMAC-SHA256
- **Thread-Safe**: Controlo de concorrência para múltiplas requisições
- **API RESTful**: Interface padronizada com documentação automática

## 🛠️ Tecnologias

- **Python 3.8+** | **FastAPI** | **SQLite** | **Pydantic** | **Uvicorn**

## 📁 Estrutura

```
health-monitoring-api/
├── main.py              # Servidor principal
├── models.py            # Modelos Pydantic
├── requirements.txt     # Dependências
├── health_data.db      # Base SQLite (auto-criada)
└── csv_data/           # Ficheiros CSV (auto-criado)
```

## 📥 Instalação

```bash
# Clonar e configurar
git clone <url-repositorio>
cd health-monitoring-api
python -m venv venv

# Ativar ambiente virtual
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

**requirements.txt:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
```

## ⚙️ Configuração

**⚠️ IMPORTANTE**: Altere a chave secreta em `main.py`:

```python
SECRET_KEY = "sua-chave-secreta-super-forte-aqui-2024"
```

## 🚀 Uso

```bash
# Iniciar servidor
python main.py
# ou
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Verificar status
curl http://localhost:8000
```

**Documentação automática:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔗 Endpoints

### `GET /` - Status da API
```bash
curl http://localhost:8000/
```

### `POST /v1/data/detailed` - Enviar Dados
```bash
curl -X POST "http://localhost:8000/v1/data/detailed" \
  -H "Content-Type: application/json" \
  -d @dados_saude.json
```

**Resposta:**
```json
{
  "status": "sucesso",
  "message": "Dados recebidos e guardados com sucesso (anonimizados).",
  "anonymousUserId": "anon_7f8e9d1c2b3a4567"
}
```

### `GET /v1/privacy/test/{user_id}` - Testar Anonimização
```bash
curl http://localhost:8000/v1/privacy/test/meu-user-123
```

## 📊 Estrutura de Dados

### Payload Exemplo
```json
{
  "userId": "usuario-original-id",
  "timestamp": 1700000000000,
  "heartRateRecords": [
    {
      "timestamp": 1700000000000,
      "bpm": 75,
      "userId": "usuario-original-id"
    }
  ],
  "steps": {
    "date": "2024-01-15",
    "hourlyCounts": {"8": 1200, "9": 1500}
  },
  "sleepSessions": [
    {
      "sessionSummary": {
        "startTime": "2024-01-14T22:30:00Z",
        "endTime": "2024-01-15T06:30:00Z",
        "durationMinutes": 480
      },
      "stages": [
        {
          "type": 1,
          "startTime": "2024-01-14T22:30:00Z",
          "endTime": "2024-01-14T23:30:00Z"
        }
      ]
    }
  ],
  "calorieRecords": [
    {
      "kilocalorias": 2100.5,
      "tipo": "BMR"
    }
  ],
  "oxygenSaturationRecords": [
    {
      "timestamp": 1700000000000,
      "spo2": 98.5
    }
  ],
  "accelerometerReadings": [
    {"timestamp": 1700000000000, "x": 0.123, "y": -0.456, "z": 9.789}
  ],
  "gyroscopeReadings": [
    {"timestamp": 1700000000000, "x": 0.001, "y": 0.002, "z": -0.001}
  ]
}
```

## 🔒 Privacidade e Segurança

### Anonimização Automática

1. **Receção**: API recebe `userId` original
2. **Hash**: Gera HMAC-SHA256 com chave secreta  
3. **Armazenamento**: Guarda apenas ID anónimo
4. **Consistência**: Mesmo utilizador = mesmo hash sempre

```
Original: "usuario-123"
         ↓ (HMAC-SHA256)
Anónimo: "anon_7f8e9d1c2b3a4567"
```
## 🗄️ Base de Dados

### Tabelas Principais

- **heart_rate**: Frequência cardíaca
- **steps**: Contagem de passos por hora
- **sleep_sessions**: Sessões de sono
- **sleep_stages**: Estágios do sono
- **calories**: Dados calóricos
- **oxygen_saturation**: Oxigenação
- **accelerometer/gyroscope**: Sensores

### Consultas Úteis

```sql
-- Utilizadores únicos
SELECT COUNT(DISTINCT userId) FROM heart_rate;

-- Média de BPM por utilizador
SELECT userId, AVG(bpm) FROM heart_rate GROUP BY userId;
```

## 📝 Logs

### Exemplo
```
--- Dados Recebidos ---
ID Original (não armazenado): usuario-123
ID Anônimo: anon_7f8e9d1c2b3a4567
Heart Rate Records: 45
Sleep Sessions: 1
--- Processamento Concluído ---
```

## 🧑‍💻 Desenvolvimento

### Testar API
```python
import httpx
response = httpx.get('http://localhost:8000')
print(response.json())
```
