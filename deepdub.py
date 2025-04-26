import sys
assert sys.version_info >= (3, 9), "Deepdub requires Python 3.9 or higher"

try:
    from deepdub import DeepdubClient
except ImportError:
    import pip
    pip.main(['install', 'deepdub'])
    from deepdub import DeepdubClient

dd = DeepdubClient(api_key="dd-MB84hb2ije2VtvkyyOwZGItP2H2p65Lx6b57bfb0")

audio_out = dd.tts(
    text="Try out one of our many use case presets.",
    voice_prompt_id="eedd9a83-eccc-4c66-b8aa-1d9eb490e57e_prompt-reading-neutral",
    model="dd-etts-1.1",
    locale="en-US",
    )
with open("Deepdub-generated-output.mp3", "wb") as f:
    f.write(audio_out)