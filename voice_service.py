"""
Voice Service - Speech-to-Text and Text-to-Speech
Handles voice input transcription and voice output generation
"""

import os
import io
import tempfile
from typing import Optional
from openai import OpenAI
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Directory for temporary audio files
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_temp")
os.makedirs(AUDIO_DIR, exist_ok=True)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Transcribe audio using OpenAI Whisper API.
    
    Args:
        audio_bytes: Raw audio data
        filename: Original filename (for format detection)
        
    Returns:
        dict with transcription or error
    """
    try:
        # Save audio to temporary file
        temp_path = os.path.join(AUDIO_DIR, filename)
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        
        # Transcribe using Whisper
        with open(temp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "success": True,
            "text": transcription.strip()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def text_to_speech_openai(text: str, voice: str = "alloy") -> Optional[bytes]:
    """
    Convert text to speech using OpenAI TTS API.
    
    Args:
        text: Text to convert
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        
    Returns:
        Audio bytes or None if error
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Get audio bytes
        audio_bytes = response.content
        return audio_bytes
        
    except Exception as e:
        print(f"OpenAI TTS Error: {e}")
        return None


def text_to_speech_gtts(text: str, lang: str = "en") -> Optional[bytes]:
    """
    Convert text to speech using Google TTS (free, no API key needed).
    Fallback option if OpenAI TTS is not available or too expensive.
    
    Args:
        text: Text to convert
        lang: Language code
        
    Returns:
        Audio bytes or None if error
    """
    try:
        # Create gTTS object
        tts = gTTS(text=text, lang=lang, slow=False)
        
        # Save to bytes buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return audio_buffer.read()
        
    except Exception as e:
        print(f"gTTS Error: {e}")
        return None


def text_to_speech(text: str, use_openai: bool = False, voice: str = "alloy") -> Optional[bytes]:
    """
    Convert text to speech.
    Uses gTTS by default (free), can optionally use OpenAI TTS.
    
    Args:
        text: Text to convert
        use_openai: Whether to use OpenAI TTS (costs money but higher quality)
        voice: OpenAI voice to use if use_openai is True
        
    Returns:
        Audio bytes or None if error
    """
    # Limit text length to avoid issues
    if len(text) > 4000:
        text = text[:4000] + "... (response truncated for audio)"
    
    if use_openai:
        return text_to_speech_openai(text, voice)
    else:
        return text_to_speech_gtts(text)


# For testing
if __name__ == "__main__":
    print("Voice Service initialized")
    print(f"Audio temp directory: {AUDIO_DIR}")
    
    # Test TTS
    test_text = "Hello! This is a test of the text to speech system."
    audio = text_to_speech(test_text)
    if audio:
        print(f"TTS test successful! Generated {len(audio)} bytes of audio")
    else:
        print("TTS test failed")
