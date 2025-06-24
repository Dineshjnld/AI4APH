"""
CCTNS Copilot Engine Runner
"""
import uvicorn
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.settings import settings

def main():
    """Run the CCTNS Copilot Engine"""
    print("🚀 Starting CCTNS Copilot Engine...")
    print(f"📍 Host: {settings.HOST}:{settings.PORT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    
    # Create necessary directories
    Path("temp").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("models_cache").mkdir(exist_ok=True)
    
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()