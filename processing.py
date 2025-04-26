import subprocess
import os
import sys

def lip_sync(input_video_path, input_audio_path, output_path):
    # Ensure working directory is Wav2Lip
    if not os.path.exists('Wav2Lip'):
        print("Error: Wav2Lip repo not found. Clone it first.")
        sys.exit(1)

    os.chdir('Wav2Lip')

    # Run Wav2Lip inference
    command = [
        'python3', 'inference.py',
        '--checkpoint_path', 'wav2lip_gan.pth',
        '--face', input_video_path,
        '--audio', input_audio_path,
        '--outfile', output_path
    ]
    
    subprocess.run(command)

    print(f"Done! Output saved to {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Lip Sync Service')
    parser.add_argument('--video', required=True, help='Path to input MP4 video')
    parser.add_argument('--audio', required=True, help='Path to input MP3 audio')
    parser.add_argument('--output', required=True, help='Path to save output video')
    
    args = parser.parse_args()

    lip_sync(args.video, args.audio, args.output)
