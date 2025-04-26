from google.cloud import speech
import grpc
import io
# from google.cloud import texttospeech

# from google.cloud import speech


def transcribe_file_with_auto_punctuation(audio_file: str) -> speech.RecognizeResponse:
    """Transcribe the given audio file with auto punctuation enabled.
    Args:
        audio_file (str): Path to the local audio file to be transcribed.
    Returns:
        speech.RecognizeResponse: The response containing the transcription results.
    """
    client = speech.SpeechClient()

    with open(audio_file, "rb") as f:
        audio_content = f.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=16000,
        language_code="en-US",
        # Enable automatic punctuation
        # enable_automatic_punctuation=True,
    )

    response = client.recognize(config=config, audio=audio)

    total_results = []

    for result in response.results:
        total_results.append(result.alternatives[0].transcript)

    return ''.join(total_results)


print(transcribe_file_with_auto_punctuation('media/way_cut_english_video.mp3'))


