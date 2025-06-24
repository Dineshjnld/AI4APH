"""
Speech-to-Text Processor using AI4Bharat IndicConformer + Whisper
"""
import torch
import torchaudio
import whisper
import logging
from pathlib import Path
from typing import Dict, Optional
import asyncio
import re

class IndianSTTProcessor:
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize models
        self._load_models()
    
    def _load_models(self):
        """Load STT models"""
        try:
            # Primary: AI4Bharat IndicConformer (simulated - replace with actual)
            self.indic_available = False  # Set to True when model is available
            
            # Fallback: Whisper
            self.whisper_model = whisper.load_model("medium")
            self.whisper_available = True
            self.logger.info("✅ Whisper model loaded")
            
        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
    
    async def transcribe_audio(self, audio_path: str, language: str = "te") -> Dict:
        """Main transcription method"""
        try:
            if self.indic_available and language in ["te", "hi", "en-IN"]:
                result = await self._transcribe_indic(audio_path, language)
                if result["confidence"] > 0.7:
                    return result
            
            if self.whisper_available:
                return await self._transcribe_whisper(audio_path, language)
            
            return {"text": "", "confidence": 0.0, "error": "No STT available"}
            
        except Exception as e:
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    async def _transcribe_whisper(self, audio_path: str, language: str) -> Dict:
        """Whisper transcription"""
        try:
            result = self.whisper_model.transcribe(
                audio_path,
                language="te" if language == "te" else "en"
            )
            
            enhanced_text = self._enhance_police_terminology(result["text"])
            
            return {
                "text": enhanced_text,
                "language": result.get("language", language),
                "confidence": 0.8,
                "model": "whisper"
            }
        except Exception as e:
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def _enhance_police_terminology(self, text: str) -> str:
        """Apply police terminology corrections"""
        corrections = {
            "fir": "FIR",
            "sho": "SHO",
            "guntur": "Guntur",
            "vijayawada": "Vijayawada",
            "visakhapatnam": "Visakhapatnam"
        }
        
        enhanced = text
        for old, new in corrections.items():
            enhanced = re.sub(old, new, enhanced, flags=re.IGNORECASE)
        
        return enhanced.strip()