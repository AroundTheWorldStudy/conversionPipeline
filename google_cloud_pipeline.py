# -*- coding: utf-8 -*-

# Prerequisites:
# 1. Install necessary libraries:
#    pip install google-cloud-speech google-cloud-translate google-cloud-texttospeech
# 2. Set up Google Cloud authentication:
#    https://cloud.google.com/docs/authentication/provide-credentials-adc
#    Ensure your environment is authenticated (e.g., using `gcloud auth application-default login`)
#    and the necessary APIs (Speech-to-Text, Translation, Text-to-Speech) are enabled
#    in your Google Cloud project.
# 3. Have an input audio file (e.g., WAV, FLAC, MP3 - ensure format compatibility
#    with Speech-to-Text API, linear16 or flac recommended for best results).

import argparse
import io
import os
from google.cloud import speech
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

def transcribe_audio_with_timestamps(audio_file_path: str) -> tuple[str, list[dict]]:
    """
    Transcribes an audio file using Google Cloud Speech-to-Text
    and returns the transcript with word timestamps.

    Args:
        audio_file_path: Path to the local audio file.

    Returns:
        A tuple containing:
        - The full transcript (string).
        - A list of word info dictionaries, each containing 'word', 'start_time', 'end_time'.
        Returns (None, []) if transcription fails.
    """
    print(f"Starting transcription for: {audio_file_path}")
    try:
        client = speech.SpeechClient()

        # Read the audio file content
        with io.open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()

        # Configure recognition settings
        # Ensure the audio encoding matches your file type.
        # Common encodings: LINEAR16, FLAC, MP3, OGG_OPUS
        # You might need to adjust sample_rate_hertz based on your audio file.
        # If unsure, you can often omit sample_rate_hertz and encoding for formats
        # like WAV where it can be inferred from the header.
        recognition_config = speech.RecognitionConfig(
            # encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # Example for WAV
            # sample_rate_hertz=16000, # Example sample rate
            language_code="en-US",  # Source language
            enable_word_time_offsets=False, # Crucial for timestamps
            # model="latest_long", # Consider using specific models for better accuracy
            # audio_channel_count=1, # Adjust if stereo
            # enable_automatic_punctuation=True, # Often helpful
        )

        audio = speech.RecognitionAudio(content=content)

        # Perform the transcription request
        # Using long_running_recognize for potentially longer audio files
        print("Sending request to Speech-to-Text API...")
        operation = client.long_running_recognize(
            config=recognition_config, audio=audio
        )
        response = operation.result(timeout=100000) # Adjust timeout as needed

        if not response.results:
            print("Warning: No transcription results received.")
            return None, []

        # Extract transcript and timestamps
        full_transcript = ""
        word_timestamps = []
        for result in response.results:
            if result.alternatives:
                alternative = result.alternatives[0]
                full_transcript += alternative.transcript + " "
                for word_info in alternative.words:
                    start_time = word_info.start_time.total_seconds()
                    end_time = word_info.end_time.total_seconds()
                    word_timestamps.append({
                        "word": word_info.word,
                        "start_time": start_time,
                        "end_time": end_time
                    })

        print("Transcription successful.")
        return full_transcript.strip(), word_timestamps

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None, []

def translate_text(text: str, target_language: str) -> str | None:
    """
    Translates text using Google Cloud Translation API.

    Args:
        text: The text to translate.
        target_language: The ISO 639-1 code for the target language (e.g., 'es', 'fr').

    Returns:
        The translated text, or None if translation fails.
    """
    if not text:
        print("No text provided for translation.")
        return None

    print(f"Starting translation to target language: {target_language}")
    try:
        translate_client = translate.Client()

        result = translate_client.translate(text, target_language=target_language)
        translated_text = result["translatedText"]

        # Basic HTML entity decoding often needed with this library version
        import html
        translated_text = html.unescape(translated_text)

        print("Translation successful.")
        return translated_text

    except Exception as e:
        print(f"Error during translation: {e}")
        return None

def synthesize_speech(text: str, target_language: str, output_filename: str) -> bool:
    """
    Synthesizes speech from text using Google Cloud Text-to-Speech API.

    Args:
        text: The text to synthesize.
        target_language: The language code for synthesis (e.g., 'es-ES', 'fr-FR').
                         Note: This might differ slightly from the translation code.
                         Check supported voices: https://cloud.google.com/text-to-speech/docs/voices
        output_filename: Path to save the output audio file (e.g., 'output.mp3').

    Returns:
        True if synthesis is successful and file is saved, False otherwise.
    """
    if not text:
        print("No text provided for speech synthesis.")
        return False

    print(f"Starting speech synthesis for language: {target_language}")
    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Select the voice. You might want to make this configurable.
        # Ensure the language_code matches the target language.
        # Example: Using a standard Spanish (Spain) voice.
        voice = texttospeech.VoiceSelectionParams(
            language_code=target_language, # e.g., 'es-ES'
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL # Or FEMALE/MALE
        )

        # Select the audio format (MP3 is common)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform the synthesis request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Save the audio content to a file
        with open(output_filename, "wb") as out:
            out.write(response.audio_content)
            print(f"Audio content written to file: {output_filename}")
        return True

    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Speech-to-Text, Translation, and Text-to-Speech Pipeline")
    parser.add_argument("audio_file", help="Path to the input English audio file (e.g., input.wav)")
    parser.add_argument("target_language", help="Target language code for translation (e.g., 'es', 'fr', 'de')")
    parser.add_argument("output_audio_file", help="Path to save the output translated audio file (e.g., output.mp3)")
    parser.add_argument("--tts_language_code", help="Optional: Specific language code for TTS voice (e.g., 'es-ES', 'fr-FR'). If not provided, attempts to derive from target_language (e.g., 'es' -> 'es-ES').")

    args = parser.parse_args()

    # --- Step 1: Transcription ---
    original_transcript, word_timestamps = transcribe_audio_with_timestamps(args.audio_file)
    print("Args:", args)

    if not original_transcript:
        print("Pipeline failed: Could not transcribe audio.")
        return

    print("\n--- Original Transcript ---")
    print(original_transcript)
    # print("\n--- Word Timestamps (Original English) ---")
    # for item in word_timestamps:
    #     print(f"  {item['word']}: {item['start_time']:.2f}s - {item['end_time']:.2f}s")

    # --- Step 2: Translation ---
    translated_text = translate_text(original_transcript, args.target_language)

    if not translated_text:
        print("Pipeline failed: Could not translate text.")
        return

    print("\n--- Translated Text ---")
    print(translated_text)
    print("\n--- NOTE: Timestamps below correspond to the *original* English words ---")
    for i, item in enumerate(word_timestamps):
         print(f"  (Original word {i+1}: {item['word']}) {item['start_time']:.2f}s - {item['end_time']:.2f}s")


    # --- Step 3: Text-to-Speech ---
    # Determine the TTS language code
    tts_language = args.tts_language_code
    if not tts_language:
        # Basic attempt to create a TTS code (may need refinement for some languages)
        if args.target_language == "en":
             tts_language = "en-US" # Default to US English if translating back to English
        elif args.target_language == "zh":
             tts_language = "cmn-CN" # Mandarin Chinese example
        else:
             tts_language = f"{args.target_language}-{args.target_language.upper()}" # e.g., es -> es-ES
        print(f"Automatically determined TTS language code: {tts_language} (verify if correct for your target)")


    success = synthesize_speech(translated_text, tts_language, args.output_audio_file)

    if success:
        print(f"\nPipeline completed successfully! Translated speech saved to {args.output_audio_file}")
    else:
        print("\nPipeline failed: Could not synthesize speech.")

if __name__ == "__main__":
    main()
