import requests
import os
import time
import json

# --- Configuration ---
DEEPDUB_API_KEY = "dd-MB84hb2ije2VtvkyyOwZGItP2H2p65Lx6b57bfb0"  # Replace with your actual API key
DEEPDUB_API_BASE_URL = "https://api.deepdub.ai" # Replace with the actual API base URL if different
LOCAL_FILE_PATH = "media/way_cut_spanish_video_wav.wav" # Replace with the path to your MP3 or WAV file
SOURCE_LANGUAGE = "en-MX" # Example: English (US) - Use ISO codes from Deepdub docs
TARGET_LANGUAGE = "es-EN" # Example: Spanish (Mexico) - Use ISO codes from Deepdub docs
OUTPUT_PRESET = "news" # Example: Use a preset from Deepdub docs (e.g., 'news', 'drama', 'corporate')
# Alternatively, you might specify a specific voice_id if available:
# VOICE_ID = "some_voice_identifier"

# --- Check if file exists ---
if not os.path.exists(LOCAL_FILE_PATH):
    print(f"Error: File not found at {LOCAL_FILE_PATH}")
    exit()

# --- Prepare API Request ---
# This is a hypothetical endpoint - check Deepdub documentation for the correct one
dubbing_endpoint = f"{DEEPDUB_API_BASE_URL}/v1/dubbing" # Or /v1/translate, /v1/speech etc.

headers = {
    "Authorization": f"Bearer {DEEPDUB_API_KEY}",
    # Add other headers if required by Deepdub docs, e.g., 'Content-Type' is often handled by requests with files
}

# Data payload - parameter names are examples, check docs
payload = {
    'source_language': SOURCE_LANGUAGE,
    'target_language': TARGET_LANGUAGE,
    'preset': OUTPUT_PRESET,
    # Add other parameters as needed, e.g.:
    # 'voice_id': VOICE_ID,
    # 'output_format': 'mp3', # If you can specify output format
}

files = {
    'file': (os.path.basename(LOCAL_FILE_PATH), open(LOCAL_FILE_PATH, 'rb'), 'audio/mpeg' if LOCAL_FILE_PATH.lower().endswith('.mp3') else 'audio/wav')
    # The third item in the tuple is the MIME type. Adjust if needed.
}

print(f"Attempting to submit '{LOCAL_FILE_PATH}' for dubbing to {TARGET_LANGUAGE}...")

try:
    # --- Make the API Call to start the job ---
    # Use 'data' for form fields and 'files' for the file upload
    response = requests.post(dubbing_endpoint, headers=headers, data=payload, files=files)

    # --- Handle the Response ---
    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

    print(f"Successfully submitted job. Status Code: {response.status_code}")

    # --- Process Asynchronous Response (Example) ---
    # The actual response structure depends heavily on Deepdub's API design.
    # It will likely contain a job ID to track progress.
    try:
        response_data = response.json()
        print("API Response:")
        print(json.dumps(response_data, indent=2))

        job_id = response_data.get('job_id') # Adjust key based on actual response

        if job_id:
            print(f"\nJob ID received: {job_id}")
            print("You will need to poll a status endpoint (e.g., /v1/jobs/{job_id})")
            print("to check when the processing is complete and get the translated audio URL.")
            # --- Placeholder for Polling Logic (Implement based on Deepdub docs) ---
            # status_endpoint = f"{DEEPDUB_API_BASE_URL}/v1/jobs/{job_id}"
            # while True:
            #     print("Checking job status...")
            #     status_response = requests.get(status_endpoint, headers=headers)
            #     status_response.raise_for_status()
            #     status_data = status_response.json()
            #     job_status = status_data.get('status') # Adjust key based on actual response
            #     print(f"Current status: {job_status}")
            #
            #     if job_status == 'completed':
            #         output_url = status_data.get('output_url') # Adjust key
            #         print(f"Job completed! Translated audio available at: {output_url}")
            #         # Add code here to download the file from output_url
            #         break
            #     elif job_status in ['failed', 'error']:
            #         print(f"Job failed: {status_data.get('error_message', 'Unknown error')}")
            #         break
            #     elif job_status in ['pending', 'processing']:
            #         print("Job still processing, waiting...")
            #         time.sleep(15) # Wait before checking again (adjust interval)
            #     else:
            #         print(f"Unknown job status: {job_status}")
            #         break

        else:
            print("\nWarning: Job ID not found in the response. Check the response details above.")
            print("The API might work synchronously for short files, or the response format differs.")

    except json.JSONDecodeError:
        print("\nCould not decode JSON response. Raw response text:")
        print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"\nError during job status check (if attempted): {e}")


except requests.exceptions.HTTPError as errh:
    print(f"HTTP Error: {errh}")
    print(f"Response Body: {errh.response.text}")
except requests.exceptions.ConnectionError as errc:
    print(f"Error Connecting: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Timeout Error: {errt}")
except requests.exceptions.RequestException as err:
    print(f"Oops: Something Else Went Wrong: {err}")
finally:
    # Ensure the file handle is closed
    if 'files' in locals() and 'file' in files:
        files['file'][1].close()