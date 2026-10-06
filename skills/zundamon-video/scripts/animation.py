"""Local PCM timing and amplitude-driven mouth states; not phoneme alignment."""
from array import array
import math
import sys
import wave


def mouth_track(wav_path, fps=24, open_threshold=.012, wide_threshold=.045):
    if not 1 <= fps <= 120 or not 0 < open_threshold < wide_threshold:
        raise ValueError("Invalid animation thresholds or FPS")
    with wave.open(str(wav_path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("Use uncompressed mono PCM16 WAV")
        sample_rate, frames = audio.getframerate(), audio.getnframes()
        samples = array("h", audio.readframes(frames))
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) != frames or frames == 0:
        raise ValueError("Empty or truncated WAV")
    duration = frames / sample_rate
    result = []
    previous, hold = 0, 0
    for frame in range(math.ceil(duration * fps)):
        start = round(frame * sample_rate / fps)
        end = min(frames, round((frame + 1) * sample_rate / fps))
        section = samples[start:end]
        rms = math.sqrt(sum(value * value for value in section) / max(1, len(section))) / 32768
        target = 0 if rms < open_threshold else 1 if rms < wide_threshold else 2
        if target == 0 or hold == 0:
            if target != previous:
                hold = 1
            previous = target
        elif hold:
            hold -= 1
        result.append({"frame": frame, "time": frame / fps, "rms": rms, "mouth": previous})
    return {"fps": fps, "sample_rate": sample_rate, "sample_frames": frames, "duration": duration,
            "method": "PCM RMS amplitude,3 sprite states; NOT phoneme/viseme synchronization",
            "open_threshold": open_threshold, "wide_threshold": wide_threshold, "frames": result}


def eye_state(time, fps=24):
    """A deterministic four-frame blink, unrelated to measured circuit timing."""
    if not math.isfinite(time) or time < 0 or not 1 <= fps <= 120:
        raise ValueError("Time must be finite and non-negative")
    phase = (time - 3.4) % 4.8
    if phase < 1 / fps or 3 / fps <= phase < 4 / fps:
        return "half"
    if phase < 3 / fps:
        return "closed"
    return "open"


def bottom_anchored_position(alpha_union, scale, canvas_size, content_right, top=260, gap=16):
    left, upper, right, bottom = alpha_union
    width, height = canvas_size
    if not (0 < scale <= 2 and 0 <= left < right and 0 <= upper < bottom):
        raise ValueError("Invalid sprite geometry")
    x = width - right * scale
    if x + left * scale < content_right + gap:
        raise ValueError("Character would cover the content")
    if top + bottom * scale < height:
        raise ValueError("Torso ends above the frame; use the full sprite and anchor it beyond the bottom")
    return x, top
