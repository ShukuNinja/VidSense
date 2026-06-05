from faster_whisper import WhisperModel
import time

print("START")

t1 = time.time()

model = WhisperModel(
    "large-v3",
    device="cuda",
    compute_type="float16"
)

print("MODEL LOADED")
print("TIME:", time.time() - t1)