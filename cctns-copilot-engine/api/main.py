"""
CCTNS Copilot Engine API
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from pathlib import Path

from config.settings import settings
from models.stt_processor import IndianSTTProcessor
from models.nl2sql_processor import NL2SQLProcessor
from models.sql_executor import SQLExecutor
from models.report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered copilot for CCTNS database queries"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Global components
stt_processor = None
nl2sql_processor = None
sql_executor = None
report_generator = None

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global stt_processor, nl2sql_processor, sql_executor, report_generator
    
    # Load configuration
    with open("config/models_config.yaml", "r") as f:
        import yaml
        config = yaml.safe_load(f)
    
    # Initialize processors
    stt_processor = IndianSTTProcessor(config["models"]["speech_to_text"])
    nl2sql_processor = NL2SQLProcessor(config["cctns_schema"])
    sql_executor = SQLExecutor(settings.ORACLE_CONNECTION_STRING)
    report_generator = ReportGenerator(config["models"]["summarization"])
    
    logging.info("🚀 CCTNS Copilot Engine started successfully")

@app.post("/api/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...), language: str = "te"):
    """Transcribe voice input to text"""
    try:
        # Save uploaded file
        file_path = f"temp/{file.filename}"
        Path("temp").mkdir(exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Transcribe
        result = await stt_processor.transcribe_audio(file_path, language)
        
        # Cleanup
        Path(file_path).unlink(missing_ok=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/process")
async def process_query(query: dict):
    """Process natural language query end-to-end"""
    try:
        text = query.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No query text provided")
        
        # Generate SQL
        sql_result = await nl2sql_processor.generate_sql(text)
        if not sql_result.get("valid"):
            return {"error": "Could not generate valid SQL", "details": sql_result}
        
        # Execute SQL
        db_result = await sql_executor.execute_sql(sql_result["sql"])
        if not db_result.get("success"):
            return {"error": "SQL execution failed", "details": db_result}
        
        # Generate report
        report_result = await report_generator.generate_report({
            "original_query": text,
            "sql": sql_result["sql"]
        }, db_result["results"])
        
        return {
            "query": text,
            "sql": sql_result["sql"],
            "results": db_result["results"][:50],  # Limit for API response
            "total_rows": db_result["row_count"],
            "summary": report_result.get("summary"),
            "chart_available": bool(report_result.get("chart_path"))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "models_loaded": {
            "stt": stt_processor is not None,
            "nl2sql": nl2sql_processor is not None,
            "sql_executor": sql_executor is not None,
            "report_gen": report_generator is not None
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )