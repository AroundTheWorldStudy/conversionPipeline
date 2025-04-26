import requests
import time

# ---------- UPDATE API KEY ----------
api_key = "sk-_iBP8OhGRM2SGqLGmQbBvw.klRquK9_FFZHvlFBq8eEiOoBJSr23Iss"  # Replace with your Sync.so API key

# ----------[OPTIONAL] UPDATE INPUT VIDEO AND AUDIO URL ----------
video_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortvid-03a10044-7741-4cfc-816a-5bccd392d1ee.mp4"  # URL to your source video
audio_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortaud-27623a4f-edab-4c6a-8383-871b18961a4a.wav"  # URL to your audio file
# ----------------------------------------

api_url = "https://api.sync.so/v2/generate"
headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

def submit_generation():
    payload = {
        "model": "lipsync-1.9.0-beta",
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
                break
            else:
                print(f"Job {job_id} failed with status: {status}")
                print(response.text)
                break
        else:
            time.sleep(10)

print("Starting lip sync generation job...")
job_id = submit_generation()
poll_job(job_id)