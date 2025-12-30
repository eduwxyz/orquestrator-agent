from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from ..database import Base

class ExecutionStatus(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.IDLE)
    command = Column(String)  # /plan, /implement, /test, /review
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # em segundos
    result = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # última execução ativa

    # Relacionamentos
    card = relationship("Card", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # info, error, warning, success, command, system
    content = Column(Text)
    sequence = Column(Integer)  # ordem do log

    # Relacionamento
    execution = relationship("Execution", back_populates="logs")