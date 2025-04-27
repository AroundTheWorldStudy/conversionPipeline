from google import genai
from google.cloud import speech

def get_correct_voice_option(audio_file: str) -> str: 
    client = genai.Client(api_key="AIzaSyCt9EYZ-gEpDVC_RmRU1kUAPiOdKqMcBqA")

    file = client.files.upload(file=audio_file)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[file,"\n\n Which chipr voice option best fits the audio file mainly consider gender? [Aoede : Female, Puck : Male, Charon : Male, Kore :  Female, Fenrir : Male, Leda : Female, Orus : Male, Zephyr : Female]. Only output the word of the voice option."]
    )

    return response


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