from google import genai
from google.cloud import storage, speech, texttospeech
from google.api_core.client_options import ClientOptions
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
import re, os, io, pydub, moviepy, time, requests
from flask import Blueprint, request, jsonify

main = Blueprint('main', __name__)
googleAPIKey = os.getenv("GOOGLE_API_KEY")
syncAPIKey = os.getenv("SYNC_API_KEY")
cloudStorageBucketURI = os.getenv("CLOUD_STORAGE_BUCKET_URI")
languages = {"Espanol": "es-US", "Francais": "fr-FR", "Deutsch": "nl-NL", "Portugues": "pt-BR", "Chinese": "cmn-CN", "Hindi": "hi-IN", "Arabic": "ar-XA"}

@main.route('/')
def home():
    return "Welcome to conversion pipeline API!"

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
    blob.download_to_filename(id)

def uploadToGoogleCloudStorage(bucketName: str, fileName: str, targetFileUri: str | None = None) -> str:
    print(f"Uploading file to Google Cloud Storage: {bucketName}/{fileName}")
    if targetFileUri is None:
        targetFileUri = fileName
    storageClient = storage.Client()
    bucket = storageClient.bucket(bucketName)
    blob = bucket.blob(targetFileUri)
    blob.upload_from_filename(fileName)
    return f"https://storage.googleapis.com/{bucketName}/{targetFileUri}"

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
        model="latest_long",
        language_code="en-US",
        enable_automatic_punctuation=True,
        enable_separate_recognition_per_channel=False,
    )

    operation = googleSpeachClient.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=3600)  # wait up to an hour

    print(response.results)

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
        2. **Duration match**: If needed, restructure sentences or pick synonyms so that **the spoken duration stays within 1% of the original.** 
        3. **Meaning preserved**: No additions or omissions—convey the exact same message.
        4. **Frequent period** use smaller sentences to allow for the translated text to be translated to speech.
        5. **No extra text**: No explanations, no metadata, just the translated text. 
        6. **Analyze speach for the language**: Contain the spoken time of ouput {targetLanguage} in close duration to the original text. Analyze the cadence of speach and the pauses in the original text to match the cadence of the translated text.

        Here is the text to translates: 
        {textToTranslate}
    """
    print(textToTranslate)
    response = geminiClient.models.generate_content(
        model="gemini-2.5-pro-preview-03-25",
        contents=prompt
    )
    return response

def textToSpeechSelectLanguage(textInput: str, title:str, audioFileUri: str, id: str, audioProfile: str, googleAPIKey: str) -> None:
    for targetLanguage in languages.values():
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
            resp = textToSpeechClient.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            segment = pydub.AudioSegment.from_file(io.BytesIO(resp.audio_content), format="mp3")
            final_audio += segment

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
    return {"response" : final_audio, "outpath" : outpath}



def get_next_id(bucketName: str) -> str:
    storageClient = storage.Client()
    bucket = storageClient.bucket(bucketName)
    blobs = bucket.list_blobs()
    ids = [int(blob.name.split("/")[0]) for blob in blobs if blob.name.split("/")[0].isdigit()]
    return str(max(ids) + 1) if ids else "1"

def createSyncedVideo(audio_url: str, video_url: str, outputDir: str):
    api_url = "https://api.sync.so/v2/generate"
    headers = {
        "x-api-key": "sk-06BEsOoqR1SLn5MSrTjUqA.XM4ikCqLiZq9L4-kurrALrhGeu7dMUFE",
        "Content-Type": "application/json"
    }
    def submit_generation():
        payload = {
            "model": "lipsync-2",
            "options": {
                "output_format": "mp4"
            },
            "input": [
                {"type": "video", "url": video_url},
                {"type": "audio", "url": audio_url}
            ]
        }
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            print("Generation submitted successfully, job id:", response.json()["id"])
            return response.json()["id"]
        else:
            print(response.text)
            raise Exception(f"Failed to submit generation: {response.status_code}")

    def poll_job(job_id):
        poll_url = f"{api_url}/{job_id}"
        while True:
            response = requests.get(poll_url, headers=headers, timeout=10)
            try:
                result = response.json()
                status = result["status"]
            except:
                print(response.text)
                raise Exception(f"Failed to poll job: {response.status_code}")
        
            terminal_statuses = ['COMPLETED', 'FAILED', 'REJECTED', 'CANCELLED']
            if status in terminal_statuses:
                if status == 'COMPLETED':
                    generated_video_url = result["outputUrl"]
                    print(f"Job {job_id} completed!")
                    print(f"Generated video URL: {generated_video_url}")
                    return generated_video_url
                else:
                    print(f"Job {job_id} failed with status: {status}")
                    print(response.text)
                    break
            else:
                time.sleep(10)
    def downloadVideo(url, filePath):
        response = requests.get(url)
        if response.status_code == 200:
            with open(filePath, 'wb') as file:
                file.write(response.content)
            print('File downloaded successfully')
        else:
            print('Failed to download file')
                    
    print("Starting lip sync generation job...")
    job_id = submit_generation()
    try:
        generated_video_url = poll_job(job_id)
        print(generated_video_url)
        downloadVideo(generated_video_url, outputDir)
        print("Generated video url:", generated_video_url)
    except:
        print("Video not generated properly")

@main.route('/build_audio_files', methods=['POST'])
def buildAudioFilesLanguage():
    audioFileUri = request.json.get('audioFileUri')
    language = request.json.get('language')
    id = request.json.get('id')
    googleAPIKey = request.json.get('googleAPIKey')
    cloudStorageBucketURI = request.json.get('cloudStorageBucketURI')

    fetchFromGoogleCloudStorage(cloudStorageBucketURI, audioFileUri)
    getFlacFromMp4(audioFileUri)
    oldAudioFileUri = audioFileUri
    audioFileUri = audioFileUri.replace(".mp4", ".flac")
    uploadToGoogleCloudStorage(cloudStorageBucketURI, audioFileUri, f"{id}/{id}.flac")
    trancscribedAudioFile = transcribeAudioFile(f"gs://{cloudStorageBucketURI}/{id}/{id}.flac", googleAPIKey)
    audioProfile = getCurrentAudioProfile(audioFileUri, googleAPIKey)
    targetLanguage = languages[language]
    print(f"Language: {language}. Language code: {targetLanguage}")
    translatedText = translateTextToOtherLanguage(trancscribedAudioFile, targetLanguage, googleAPIKey)
    outputMetadata = textToSpeechSelectLanguage(translatedText.text, audioFileUri, targetLanguage, id, audioProfile.text, googleAPIKey)
    video = uploadToGoogleCloudStorage(cloudStorageBucketURI, oldAudioFileUri, f"{id}/{id}.mp4")
  
    sound = pydub.AudioSegment.from_mp3(outputMetadata['outpath'])
    newOutputMetda = outputMetadata['outpath'].replace(".mp3", ".wav")
    sound.export(newOutputMetda, format="wav")
    audio = uploadToGoogleCloudStorage(cloudStorageBucketURI, newOutputMetda)

    createSyncedVideo(audio, video, f"{targetLanguage}_output.mp4")

    uploadToGoogleCloudStorage(cloudStorageBucketURI, f"{targetLanguage}_output.mp4", f"{id}/{targetLanguage}_output.mp4")

    if not audioFileUri or not language or not id or not googleAPIKey:
        return jsonify({"error": "Missing required parameters"}), 400

def aggregateDefinitionToBuildAudiofiles(audioFileUri: str,  bucketName: str, googleAPIKey: str) -> None:
    id = get_next_id(bucketName)
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
        uploadToGoogleCloudStorage(bucketName, outputMetadata["outpath"])
        createSyncedVideo(outputMetadata['outpath'], audioFileUri)