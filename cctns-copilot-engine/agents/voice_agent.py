"""
Voice Agent for handling speech-to-text and voice processing
"""
import asyncio
from typing import Dict, Any
from .base_agent import BaseAgent
from models.stt_processor import IndianSTTProcessor
from models.text_processor import TextProcessor

class VoiceAgent(BaseAgent):
    """Agent specialized in voice input processing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("VoiceAgent", config)
        
        # Initialize voice processors
        self.stt_processor = IndianSTTProcessor(config.get("stt", {}))
        self.text_processor = TextProcessor(config.get("text_processing", {}))
        
        # Voice-specific settings
        self.supported_languages = ["te", "hi", "en", "auto"]
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice input through STT and text enhancement"""
        
        processing_type = input_data.get("type", "audio_file")
        
        if processing_type == "audio_file":
            return await self._process_audio_file(input_data)
        elif processing_type == "audio_stream":
            return await self._process_audio_stream(input_data)
        elif processing_type == "text_enhancement":
            return await self._process_text_enhancement(input_data)
        else:
            raise ValueError(f"Unsupported processing type: {processing_type}")
    
    async def _process_audio_file(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded audio file"""
        audio_path = input_data.get("audio_path")
        language = input_data.get("language", "auto")
        
        if not audio_path:
            raise ValueError("Audio path is required")
        
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
        
        # Step 1: Speech-to-Text
        stt_result = await self.stt_processor.transcribe_audio(audio_path, language)
        
        if not stt_result.get("text"):
            return {
                "transcription": "",
                "enhanced_text": "",
                "confidence": 0.0,
                "error": stt_result.get("error", "Transcription failed")
            }
        
        # Step 2: Text Enhancement
        if stt_result["confidence"] >= self.confidence_threshold:
            text_result = await self.text_processor.process_text(
                stt_result["text"],
                stt_result.get("language", "en")
            )
            
            return {
                "transcription": stt_result["text"],
                "enhanced_text": text_result["final"],
                "confidence": stt_result["confidence"],
                "language": stt_result.get("language"),
                "model_used": stt_result.get("model"),
                "corrections_applied": text_result.get("corrections_applied", []),
                "processing_steps": {
                    "stt": stt_result,
                    "text_processing": text_result
                }
            }
        else:
            return {
                "transcription": stt_result["text"],
                "enhanced_text": stt_result["text"],
                "confidence": stt_result["confidence"],
                "warning": f"Low confidence ({stt_result['confidence']:.2f}), minimal processing applied"
            }
    
    async def _process_audio_stream(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process real-time audio stream"""
        # TODO: Implement real-time streaming STT
        raise NotImplementedError("Audio streaming not yet implemented")
    
    async def _process_text_enhancement(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text enhancement only (no STT)"""
        text = input_data.get("text")
        language = input_data.get("language", "en")
        
        if not text:
            raise ValueError("Text is required for enhancement")
        
        text_result = await self.text_processor.process_text(text, language)
        
        return {
            "original_text": text,
            "enhanced_text": text_result["final"],
            "confidence": text_result.get("confidence", 0.8),
            "corrections_applied": text_result.get("corrections_applied", []),
            "processing_details": text_result
        }
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate voice agent input"""
        processing_type = input_data.get("type", "audio_file")
        
        if processing_type == "audio_file":
            if "audio_path" not in input_data:
                return {"valid": False, "reason": "audio_path is required for audio_file type"}
        
        elif processing_type == "text_enhancement":
            if "text" not in input_data:
                return {"valid": False, "reason": "text is required for text_enhancement type"}
        
        language = input_data.get("language", "auto")
        if language not in self.supported_languages:
            return {"valid": False, "reason": f"Unsupported language: {language}"}
        
        return {"valid": True}
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return self.supported_languages.copy()
    
    def get_voice_stats(self) -> Dict[str, Any]:
        """Get voice processing statistics"""
        base_stats = self.get_status()
        
        # Add voice-specific stats
        voice_stats = {
            "supported_languages": self.supported_languages,
            "confidence_threshold": self.confidence_threshold,
            "stt_processor_available": self.stt_processor is not None,
            "text_processor_available": self.text_processor is not None
        }
        
        return {**base_stats, "voice_specific": voice_stats}