from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class AccelerometerData(BaseModel):
    timestamp: int
    x: float
    y: float
    z: float

class GyroscopeData(BaseModel):
    timestamp: int
    x: float
    y: float
    z: float

class BatimentoCardiaco(BaseModel):
    timestamp: int
    healthConnectId: str
    bpm: int
    zoneOffset: Optional[str] = None
    userId: str

class HourlyStepsPayload(BaseModel):
    date: str
    hourlyCounts: Dict[int, int]

class SleepStage(BaseModel):
    id: int
    sessionId: str
    type: int
    startTime: str  
    endTime: str

class Sono(BaseModel):
    healthConnectId: str
    startTime: str
    endTime: Optional[str] = None  
    durationMinutes: Optional[int] = None  
    remSleepDurationMinutes: Optional[int] = None
    deepSleepDurationMinutes: Optional[int] = None
    lightSleepDurationMinutes: Optional[int] = None
    awakeDurationMinutes: Optional[int] = None
    userId: str

class SleepSessionPayload(BaseModel):
    sessionSummary: Sono
    stages: List[SleepStage]

class Calorias(BaseModel):
    healthConnectId: str
    startTime: str
    endTime: str
    kilocalorias: float
    tipo: str
    userId: str

class OxigenacaoSanguinea(BaseModel):
    timestamp: int
    healthConnectId: str
    spo2: float
    zoneOffset: Optional[str] = None
    userId: str

class RawSpO2Data(BaseModel):
    timestamp: int
    raw: int
    a: int
    b: int
    c: int

class RawPpgData(BaseModel):
    timestamp: int
    raw: int
    max: int
    min: int
    diff: int

class RingAccelerometerData(BaseModel):
    timestamp: int
    x: float
    y: float
    z: float

class DetailedHealthAndSensorPayload(BaseModel):
    userId: str
    timestamp: int
    heartRateRecords: List[BatimentoCardiaco]
    steps: HourlyStepsPayload
    sleepSessions: List[SleepSessionPayload]
    calorieRecords: List[Calorias]
    oxygenSaturationRecords: List[OxigenacaoSanguinea]
    accelerometerReadings: List[AccelerometerData]
    gyroscopeReadings: List[GyroscopeData]
    rawSpO2Readings: List[RawSpO2Data] = Field(default_factory=list)
    rawPpgReadings: List[RawPpgData] = Field(default_factory=list)
    ringAccelerometerReadings: List[RingAccelerometerData] = Field(default_factory=list)