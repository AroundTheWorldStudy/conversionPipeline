#from Flask import Flask, request, jsonify
from google import genai
from google.cloud import storage, speech, texttospeech
from google.api_core.client_options import ClientOptions
import google.auth
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
import re, os, io, pydub, moviepy

googleAPIKey = os.getenv("GOOGLE_API_KEY")
cloudStorageBucketURI = os.getenv("CLOUD_STORAGE_BUCKET_URI")

def _split_text_to_chunks(text: str, max_chars: int = 4500) -> list[str]:
    parts = re.split(r'([\.!\?]\s)', text)
    chunks, buf = [], ''
    for part in parts:
        if len(buf) + len(part) <= max_chars:
            buf += part
        else:
            chunks.append(buf)
            buf = part
    if buf:
        chunks.append(buf)
    return chunks

def fetchFromGoogleCloudStorage(bucketName: str, id: str) -> None:
    print(f"Fetching file from Google Cloud Storage: {bucketName}/{id}")
    storageClient  = storage.Client()
    bucket = storageClient.bucket(bucketName)
    blob = bucket.blob(id)
    if not os.path.exists(id):
        os.makedirs(os.path.dirname(id), exist_ok=True)
    blob.download_to_filename(id)

def uploadToGoogleCloudStorage(bucketName: str, fileName: str, targetFileUri: str | None = None) -> None:
    print(f"Uploading file to Google Cloud Storage: {bucketName}/{fileName}")
    if targetFileUri is None:
        targetFileUri = fileName
    storageClient = storage.Client()
    bucket = storageClient.bucket(bucketName)
    blob = bucket.blob(targetFileUri)
    blob.upload_from_filename(fileName)

def getFlacFromMp4(audioFileUri: str) -> None:
    clip = moviepy.VideoFileClip(audioFileUri)
    newAudioFileUri = audioFileUri.replace(".mp4", ".flac")
    clip.audio.write_audiofile(newAudioFileUri, codec="flac", ffmpeg_params=["-sample_fmt", "s16", "-ac", "1"])
    
def getCurrentAudioProfile(audioFileUri: str, googleAPIKey: str) -> str: 
    print(f"Getting current audio profile for: {audioFileUri}")
    geminiClient = genai.Client(api_key=googleAPIKey)
    file = geminiClient.files.upload(file=audioFileUri)
    respone = geminiClient.models.generate_content(
        model="gemini-2.5-flash-preview-04-17",
        contents=[file,"\n\n Which chipr voice option best fits the audio file? [Aoede, Puck, Charon, Kore, Fenrir, Leda, Orus, Zephyr]. Only output the name of the voice option (Only the key from the list)."]
    )
    print(f"Response: {respone.text}")
    return respone

def transcribeAudioFile(gcs_uri: str, googleAPIKey: str) -> speech.RecognizeResponse:
    print(f"Transcribing audio file: {gcs_uri}")
    googleSpeachClient = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        language_code="en-US",
        enable_automatic_punctuation=True,
        enable_separate_recognition_per_channel=False,
    )

    operation = googleSpeachClient.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=3600)  # wait up to an hour

    # 3) stitch every chunk together
    transcripts = [r.alternatives[0].transcript for r in response.results]
    return " ".join(transcripts).strip()

def translateTextToOtherLanguage(textToTranslate: str, targetLanguage: str, googleAPIKey: str) -> str:
    geminiClient = genai.Client(api_key=googleAPIKey)
    prompt = f"""You are a professional translation engine.
        When I give you:
        - Source: a block of English text.
        - Target: {targetLanguage}

        Your output must be **only** the translated text in the target language—no notes, no metadata.

        **Strict requirements:**
        2. **Duration match**: If needed, restructure sentences or pick synonyms so that the spoken duration stays within ±5% of the original.  
        3. **Meaning preserved**: No additions or omissions—convey the exact same message.
        4. **Frequent period** use smaller sentences to allow for the translated text to be translated to speech.

        Here is the text to translates: 
        {textToTranslate}
    """
    print(textToTranslate)
    response = geminiClient.models.generate_content(
        model="gemini-2.5-pro-preview-03-25",
        contents=prompt
    )
    return response

def textToSpeechSelectLanguage(textInput: str, audioFileUri: str, targetLanguage: str, id: str, audioProfile: str, googleAPIKey: str) -> None:
    textToSpeechClient = texttospeech.TextToSpeechClient(client_options=ClientOptions(api_key=googleAPIKey))
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    voice = texttospeech.VoiceSelectionParams(
        language_code=targetLanguage,
        name=f"{targetLanguage}-Chirp3-HD-{audioProfile}".replace('\n', ''),
    )
    chunks = _split_text_to_chunks(textInput)
    final_audio = pydub.AudioSegment.empty()
    for chunk in chunks:
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        resp = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_cfg
        )
        segment = pydub.AudioSegment.from_file(io.BytesIO(resp.audio_content), format="mp3")
        final_audio += segment
    response = textToSpeechClient.synthesize_speech(
        input=formatedText,
        voice=voice,
        audio_config=audio_config,
    )
    orig_duration = FLAC(audioFileUri).info.length
    print(orig_duration)
    resp_duration = len(final_audio) / 1000.0
    speed_ratio = resp_duration / orig_duration
    new_frame_rate = int(final_audio.frame_rate * speed_ratio)
    sped_up = final_audio._spawn(
        final_audio.raw_data,
        overrides={"frame_rate": new_frame_rate}
    ).set_frame_rate(final_audio.frame_rate)
    final_duration = len(sped_up) / 1000.0
    print(f"Adjusted to {final_duration:.3f}s (target {orig_duration:.3f}s)")
    print(f"Speed ratio: {speed_ratio:.3f}")
    outpath = f"{id}/{targetLanguage}_output.mp3"
    outdir  = os.path.dirname(outpath)
    os.makedirs(outdir, exist_ok=True)
    sped_up.export(outpath, format="mp3")
    return {"response" : response, "outpath" : outpath}


def aggregateDefinitionToBuildAudiofiles(audioFileUri: str,  bucketName: str, id: str, googleAPIKey: str) -> None:
    fetchFromGoogleCloudStorage(bucketName, audioFileUri)
    languages = {"Espanol": "es-US", "Francais": "fr-FR", "Deutsch": "nl-NL", "Portugues": "pt-BR", "Chinese": "cmn-CN", "Hindi": "hi-IN", "Arabic": "ar-XA"}
    getFlacFromMp4(audioFileUri)
    audioFileUri = audioFileUri.replace(".mp4", ".flac")
    uploadToGoogleCloudStorage(bucketName, audioFileUri, f"{id}/{id}.flac")
    transcribedAudioFile = transcribeAudioFile(f"gs://{bucketName}/{id}/{id}.flac", googleAPIKey)
    audioProfile = getCurrentAudioProfile(audioFileUri, googleAPIKey)
    for language, targetLanguage in languages.items():
        print(f"Language: {language}. Language code: {targetLanguage}")
        translatedText = translateTextToOtherLanguage(transcribedAudioFile, language, googleAPIKey)
        outputMetadata = textToSpeechSelectLanguage(translatedText.text, audioFileUri, targetLanguage, id, audioProfile.text, googleAPIKey)
        uploadToGoogleCloudStorage(bucketName, f"{outputMetadata["outpath"]}")

if __name__ == "__main__":
    aggregateDefinitionToBuildAudiofiles("media/english_video.mp4", cloudStorageBucketURI, "1", googleAPIKey)