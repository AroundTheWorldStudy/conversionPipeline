from google import genai
from google.cloud import speech
from google.cloud import texttospeech

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
        # enable_word_time_offsets=True TODO determine how this is necessary when doing speech to text
        # Enable automatic punctuation
        # enable_automatic_punctuation=True,
    )

    response = client.recognize(config=config, audio=audio)

    total_results = []

    for result in response.results:
        total_results.append(result.alternatives[0].transcript)

    return ''.join(total_results)

def translate_text(text_to_translate, target_language):
    try:
        api_key = "AIzaSyB6lAvj-GFGB8X7KRwkPDmO8KyhO5SozGc"
        if not api_key:
            raise ValueError("API key not found. Please set the GOOGLE_API_KEY environment variable.")
        genai.configure(api_key=api_key)
    except ValueError as e:
        print(f"Error: {e}")
        exit()

    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"Translate the following text from English to {target_language} and just include the text translation, nothing else. Also include frequent periods:\n\n---\n{text_to_translate}\n---"

    try:
        response = model.generate_content(prompt)
        translated_text = response.text

    except Exception as e:
        print(f"An error occurred during API call: {e}")
    
    return translated_text

def text_to_user_language(text_to_change, target_language, name):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text_to_change)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
        language_code=target_language,
        name=f"{target_language}-Chirp3-HD-{name}",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config,
    )

    # The response's audio_content is binary.
    with open(f"{target_language}_output.mp3", "wb") as out:
        out.write(response.audio_content)
        print(f"Audio content written to file {target_language}_output.mp3")


if __name__ == "__main__":
    languages = ["Espanol", "Francais", "Deutsch", "Portugues", "Chinese", "Hindi", "Arabic"]
    language_codes = ["es-US", "fr-FR", "nl-NL", "pt-BR", "cmn-CN", "hi-IN", "ar-XA"]


    english_text = transcribe_file_with_auto_punctuation('media/way_cut_english_video.mp3')

    for i, (language, language_code) in enumerate(zip(languages, language_codes)):
        print(f"Language: {language}. Language code: {language_code}")
        other_text = translate_text(english_text, language)

        text_to_user_language(other_text, language_code, "Charon")