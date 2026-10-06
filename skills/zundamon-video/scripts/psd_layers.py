"""Small PSDv1/RGB8/RLE reader for simple flat, normal/pass-through standing art.

Not a general Photoshop renderer. Unsupported masks, effects, nested groups,
clipping or blends are rejected. Supply your own licensed artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image, ImageChops


def require(ok, message):
    if not ok:
        raise ValueError(message)


def packbits(data, width):
    output = bytearray()
    position = 0
    while position < len(data):
        code = data[position]
        position += 1
        if code < 128:
            count = code + 1
            require(position + count <= len(data), "Truncated PackBits literal")
            output.extend(data[position:position + count])
            position += count
        elif code > 128:
            require(position < len(data), "Truncated PackBits repeat")
            output.extend(bytes([data[position]]) * (257 - code))
            position += 1
        require(len(output) <= width, "PackBits row exceeds declared width")
    require(len(output) == width, "PackBits row does not match declared width")
    return bytes(output)


class FlatPsd:
    def __init__(self, path, expected_sha256=None):
        self.path = Path(path)
        require(0 < self.path.stat().st_size <= 64 * 1024 * 1024, "PSD must be at most64MiB")
        self.raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        if expected_sha256 is not None:
            require(self.sha256 == expected_sha256, "PSD SHA-256 differs from the approved input")
        self.position = 0
        signature, version, reserved, channels, height, width, depth, mode = struct.unpack(">4sH6sHIIHH", self.take(26))
        require((signature, version, reserved, depth, mode) == (b"8BPS", 1, bytes(6), 8, 3), "Only PSDv1 RGB8 is supported")
        require(0 < width <= 4096 and 0 < height <= 4096 and channels == 4, "Unsupported canvas/channels")
        self.size = (width, height)
        for _ in range(2):
            self.take(self.number(">I"))
        section_end = self.position + 4 + self.number(">I")
        layer_end = self.position + 4 + self.number(">I")
        count = abs(self.number(">h"))
        require(0 < count <= 256, "Unsupported layer count")
        self.layers = []
        for index in range(count):
            top, left, bottom, right = struct.unpack(">iiii", self.take(16))
            channel_count = self.number(">H")
            require(channel_count == 4, "Only four-channel layers are supported")
            channel_info = [(self.number(">h"), self.number(">I")) for _ in range(channel_count)]
            require(self.take(4) == b"8BIM", "Invalid layer signature")
            blend = self.take(4).decode("ascii")
            opacity, clipping, flags, filler = self.take(4)
            extra_end = self.position + 4 + self.number(">I")
            mask = self.take(self.number(">I"))
            ranges = self.take(self.number(">I"))
            length = self.number(">B")
            name = self.take(length).decode("latin-1")
            self.take((-(length + 1)) % 4)
            section = 0
            while self.position + 12 <= extra_end:
                signature, key = self.take(4), self.take(4)
                require(signature in (b"8BIM", b"8B64"), "Invalid tagged-block signature")
                length = self.number(">I")
                block = self.take(length)
                if length % 2:
                    self.take(1)
                require(key in (b"luni", b"lsct"), "Unsupported PSD layer metadata: " + repr(key))
                if key == b"luni":
                    require(len(block) >= 4, "Truncated Unicode name")
                    letters = struct.unpack(">I", block[:4])[0]
                    require(4 + letters * 2 <= len(block), "Truncated Unicode name")
                    name = block[4:4 + letters * 2].decode("utf-16be")
                else:
                    require(len(block) >= 4, "Truncated section divider")
                    section = struct.unpack(">I", block[:4])[0]
            require(self.position <= extra_end <= layer_end, "Invalid layer-extra bounds")
            self.take(extra_end - self.position)
            require(blend in ("norm", "pass") and opacity == 255 and clipping == 0
                    and not mask and not ranges, "Masks, clipping, opacity, effects or blends are unsupported")
            require(0 <= left < right <= width and 0 <= top < bottom <= height, "Layer exceeds canvas")
            require(section in (0, 1, 2, 3), "Unsupported section type")
            self.layers.append({"id": index, "name": name, "rect": (left, top, right, bottom),
                                "blend": blend, "flags": flags, "section": section, "channel_info": channel_info})
        for layer in self.layers:
            layer["channels"] = {}
            for identifier, length in layer.pop("channel_info"):
                require(identifier in (0, 1, 2, -1) and identifier not in layer["channels"], "Unsupported/duplicate channel")
                block = self.take(length)
                require(len(block) >= 2 and struct.unpack(">H", block[:2])[0] == 1, "Only RLE channel data is supported")
                layer["channels"][identifier] = block
            require(set(layer["channels"]) == {0, 1, 2, -1}, "Missing RGBA channel")
        require(self.position <= layer_end <= section_end <= len(self.raw), "Invalid PSD section lengths")
        self.groups = {}
        pending = None
        for layer in self.layers:
            if layer["section"] == 3:
                require(pending is None, "Nested groups are unsupported")
                pending = []
            elif layer["section"] in (1, 2):
                require(pending is not None and layer["blend"] == "pass" and not layer["flags"] & 2,
                        "Unsupported group")
                require(layer["name"] not in self.groups, "Duplicate group name")
                for child in pending:
                    child["group"] = layer["name"]
                self.groups[layer["name"]] = pending
                pending = None
            elif pending is not None:
                pending.append(layer)
        require(pending is None, "Unclosed layer group")
        self.cache = {}

    def take(self, count):
        require(count >= 0 and self.position + count <= len(self.raw), "PSD block exceeds file")
        result = self.raw[self.position:self.position + count]
        self.position += count
        return result

    def number(self, format):
        return struct.unpack(format, self.take(struct.calcsize(format)))[0]

    def metadata(self):
        return {"file": self.path.name, "sha256": self.sha256, "file_format_version": 1,
                "canvas_px": self.size, "supported": "RGB8/RLE/normal/flat pass-through groups only",
                "groups": {name: [{"id": layer["id"], "name": layer["name"],
                                  "saved_visible": not bool(layer["flags"] & 2)}
                                 for layer in layers] for name, layers in self.groups.items()}}

    def decode_layer(self, layer):
        left, top, right, bottom = layer["rect"]
        width, height = right - left, bottom - top
        channels = {}
        for identifier, block in layer["channels"].items():
            require(len(block) >= 2 + 2 * height, "Truncated RLE row table")
            lengths = struct.unpack(">" + "H" * height, block[2:2 + 2 * height])
            position, rows = 2 + 2 * height, []
            for length in lengths:
                require(position + length <= len(block), "RLE row exceeds channel")
                rows.append(packbits(block[position:position + length], width))
                position += length
            require(position == len(block), "Unconsumed channel bytes")
            channels[identifier] = Image.frombytes("L", (width, height), b"".join(rows))
        return Image.merge("RGBA", [channels[key] for key in (0, 1, 2, -1)])

    def compose(self, choices=None):
        choices = choices or {}
        require(set(choices) <= set(self.groups), "Unknown group selection")
        selected = {}
        for group, name in choices.items():
            matches = [layer for layer in self.groups[group] if layer["name"] == name]
            require(len(matches) == 1, "Unknown or ambiguous layer selection: " + group + "/" + name)
            selected[group] = matches[0]["id"]
        image = Image.new("RGBA", self.size)
        active = []
        for layer in self.layers:
            if layer["section"]:
                continue
            group = layer.get("group")
            visible = layer["id"] == selected[group] if group in selected else not bool(layer["flags"] & 2)
            if visible:
                require(layer["blend"] == "norm", "Raster layer must use normal blend")
                if layer["id"] not in self.cache:
                    self.cache[layer["id"]] = self.decode_layer(layer)
                image.alpha_composite(self.cache[layer["id"]], layer["rect"][:2])
                active.append(layer["id"])
        return image, active

    def check_merged(self):
        with Image.open(self.path) as opened:
            saved = opened.convert("RGBA")
        rebuilt, _ = self.compose()
        result = {}
        for background in ("white", "black"):
            first = Image.new("RGBA", self.size, background)
            second = first.copy()
            first.alpha_composite(saved)
            second.alpha_composite(rebuilt)
            difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
            histogram = difference.histogram()
            mean = sum((i % 256) * n for i, n in enumerate(histogram)) / (self.size[0] * self.size[1] * 3)
            maximum = max(high for low, high in difference.getextrema())
            require(mean < .02 and maximum <= 2, "Unsupported composition differs from the saved merged image")
            result[background] = {"mean_error": mean, "max_error": maximum}
        alpha = ImageChops.difference(saved.getchannel("A"), rebuilt.getchannel("A"))
        require(alpha.getextrema()[1] <= 1, "Alpha differs beyond8-bit composition rounding")
        result["alpha_max_error"] = alpha.getextrema()[1]
        result["byte_identical"] = False
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--choices", type=Path, help="JSON mapping exact group names to exact layer names")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    art = FlatPsd(args.input, args.sha256)
    check = art.check_merged()
    if args.output:
        require(not args.output.exists(), "Do not overwrite a previous sprite")
        choices = json.loads(args.choices.read_text()) if args.choices else {}
        image, active = art.compose(choices)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.output)
        print(json.dumps({"active_layer_ids": active, "comparison": check}, ensure_ascii=False))
    else:
        print(json.dumps({"metadata": art.metadata(), "comparison": check}, ensure_ascii=False, indent=2))
