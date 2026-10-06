"""Synthetic fixtures only: no character artwork, model or human voice is bundled."""
from array import array
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/zundamon-video/scripts"))
from animation import bottom_anchored_position, eye_state, mouth_track
from psd_layers import FlatPsd, packbits


def tiny_psd():
    header = struct.pack(">4sH6sHIIHH", b"8BPS", 1, bytes(6), 4, 2, 2, 8, 3)
    blocks = []
    for value in (128, 64, 32, 255):
        blocks.append(struct.pack(">HHH", 1, 3, 3) + bytes([1, value, value]) * 2)
    channels = b"".join(struct.pack(">hI", identifier, len(block))
                        for identifier, block in zip((0, 1, 2, -1), blocks))
    name = b"\x04body" + bytes(3)
    extra = struct.pack(">II", 0, 0) + name
    record = struct.pack(">iiiiH", 0, 0, 2, 2, 4) + channels
    record += b"8BIMnorm" + bytes([255, 0, 8, 0]) + struct.pack(">I", len(extra)) + extra
    layers = struct.pack(">h", -1) + record + b"".join(blocks)
    section = struct.pack(">I", len(layers)) + layers + struct.pack(">I", 0)
    merged = struct.pack(">H", 0) + b"".join(bytes([value]) * 4 for value in (128, 64, 32, 255))
    return header + struct.pack(">II", 0, 0) + struct.pack(">I", len(section)) + section + merged


class PsdTests(unittest.TestCase):
    def test_packbits_literal_repeat_and_noop(self):
        self.assertEqual(packbits(bytes([1, 4, 5, 254, 8, 128]), 5), bytes([4, 5, 8, 8, 8]))

    def test_truncated_or_oversized_packbits_rejected(self):
        for data, width in ((b"\x02\x01", 3), (b"\xff", 2), (b"\xfe\x01", 2), (b"", 1)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                packbits(data, width)

    def test_small_self_authored_psd_matches_merged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.psd"
            path.write_bytes(tiny_psd())
            art = FlatPsd(path, hashlib.sha256(path.read_bytes()).hexdigest())
            result = art.check_merged()
            self.assertEqual(result["alpha_max_error"], 0)
            image, active = art.compose()
            self.assertEqual(image.getpixel((0, 0)), (128, 64, 32, 255))
            self.assertEqual(active, [0])

    def test_wrong_hash_or_unsupported_blend_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.psd"
            path.write_bytes(tiny_psd())
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                FlatPsd(path, "0" * 64)
            path.write_bytes(tiny_psd().replace(b"8BIMnorm", b"8BIMmul "))
            with self.assertRaises(ValueError):
                FlatPsd(path)


class AnimationTests(unittest.TestCase):
    def test_synthetic_amplitude_changes_mouth_and_silence_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic-not-speech.wav"
            values = array("h", [4000] * 2400 + [1000] * 2400 + [0] * 3200)
            if sys.byteorder != "little":
                values.byteswap()
            with wave.open(str(path), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(8000)
                stream.writeframes(values.tobytes())
            track = mouth_track(path)
            self.assertEqual(track["duration"], 1)
            self.assertEqual(track["frames"][2]["mouth"], 2)
            self.assertEqual(track["frames"][10]["mouth"], 1)
            self.assertTrue(all(frame["mouth"] == 0 for frame in track["frames"] if frame["time"] >= .65))
            self.assertIn("NOT phoneme", track["method"])

    def test_body_continuity_and_content_separation(self):
        self.assertEqual(bottom_anchored_position((0, 0, 100, 200), 1, (500, 300), 350, top=150), (400, 150))
        with self.assertRaisesRegex(ValueError, "Torso"):
            bottom_anchored_position((0, 0, 100, 200), 1, (500, 300), 350, top=50)
        with self.assertRaisesRegex(ValueError, "cover"):
            bottom_anchored_position((0, 0, 100, 200), 1, (500, 300), 450, top=150)

    def test_blink_is_bounded(self):
        self.assertEqual(eye_state(1), "open")
        self.assertEqual(eye_state(3.46), "closed")
        with self.assertRaises(ValueError):
            eye_state(-1)


if __name__ == "__main__":
    unittest.main()
