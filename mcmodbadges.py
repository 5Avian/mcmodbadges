import binascii
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

ADDRESS = "localhost"
PORT = 8080

PROJECT_URL = "https://api.modrinth.com/v2/project/%s"
FABRIC_WHITE = (246, 246, 246, 255)
FABRIC_BROWN = (56, 52, 42, 255)

ui = Path("mcmodbadges_ui.html").read_text().encode()
regular = ImageFont.truetype("Minecraft.otf", 56)
bold = ImageFont.truetype("Minecraft-Bold.otf", 56)


# Parses an RGB or RGBA hex string into a tuple containing an RGBA color.
def parse_hex_color(string: str) -> tuple[int, int, int, int]:
    string = string.removeprefix("#")
    color = binascii.unhexlify(string)
    match len(color):
        case 1:
            return (color[0], color[0], color[0], 255)
        case 2:
            return (color[0], color[0], color[0], color[1])
        case 3:
            return (color[0], color[1], color[2], 255)
        case 4:
            return (color[0], color[1], color[2], color[3])
        case _:
            raise ValueError("hex string must contain 1, 2, 3, or 4 bytes")


# Returns the offset necessary to center an element of `len` when compared to `cmp_len`.
def calc_center_offset(len: float, cmp_len: float) -> float:
    offset = max(cmp_len - len, 0)
    if offset > 0:
        offset = offset / 2
    return offset


# Returns the name of the class of the argument, optionally prefixed with its module.
def class_name(obj: Any) -> str:
    clazz = obj.__class__
    if clazz.__module__ and clazz.__module__ != "builtins":
        return clazz.__module__ + "." + clazz.__name__
    else:
        return clazz.__name__


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            url = urlparse(self.path)
            if url.path == "/ui":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(ui)
                return
            elif url.path != "/":
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                return
            params = parse_qs(url.query, keep_blank_values=True)

            mod_id = params["mod_id"][0] if "mod_id" in params else "fabric-api"
            top_text = params["top_text"][0] if "top_text" in params else "Requires"
            bot_text = params["bot_text"][0] if "bot_text" in params else None
            bg_fill = (
                parse_hex_color(params["bg_fill"][0])
                if "bg_fill" in params
                else FABRIC_WHITE
            )
            top_fill = (
                parse_hex_color(params["top_fill"][0])
                if "top_fill" in params
                else FABRIC_BROWN
            )
            bot_fill = (
                parse_hex_color(params["bot_fill"][0])
                if "bot_fill" in params
                else FABRIC_BROWN
            )
            top_centered = "top_centered" in params
            bot_centered = "bot_centered" in params

            with urlopen(PROJECT_URL % mod_id) as res:
                project = json.load(res)
            if bot_text == None:
                bot_text = project["title"]
            with urlopen(project["icon_url"]) as res:
                icon = Image.open(res)
            icon = icon.resize((128, 128), Image.Resampling.NEAREST).convert("RGBA")

            top_len = regular.getlength(top_text)
            bot_len = bold.getlength(bot_text)
            width = 128 + 12 + round(max(top_len, bot_len)) + 12
            top_offset = (
                round(calc_center_offset(top_len, bot_len)) if top_centered else 0
            )
            bot_offset = (
                round(calc_center_offset(bot_len, top_len)) if bot_centered else 0
            )

            badge = Image.new("RGBA", (width, 128), bg_fill)
            badge.paste(icon, (0, 0), icon)
            draw = ImageDraw.Draw(badge)
            draw.text((140 + top_offset, 4), top_text, top_fill, regular)
            draw.text((140 + bot_offset, 68), bot_text, bot_fill, bold)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Disposition", f"inline; filename={mod_id}.png")
            self.end_headers()
            badge.save(self.wfile, "PNG")
        except Exception as ex:
            print(f"{class_name(ex)}: {ex}")
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.end_headers()


def main():
    server = HTTPServer((ADDRESS, PORT), RequestHandler)
    server.serve_forever()
    server.server_close()


if __name__ == "__main__":
    main()
