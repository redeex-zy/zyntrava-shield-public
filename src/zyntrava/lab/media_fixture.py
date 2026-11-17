"""Owned text/PDF/HTTP fixture transport; not an arbitrary document ingestion API."""

import html
import io
import re
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import httpx


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def text_pdf(text: str) -> bytes:
    # Small uncompressed owned fixture; no attachments, scripts, links or OCR.
    lines = [
        part
        for line in text.replace("\t", " ").splitlines()
        for part in (
            textwrap.wrap(
                line,
                width=95,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=False,
            )
            or [""]
        )
    ]
    operations = ["BT /F1 9 Tf 36 800 Td 12 TL"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        operations.append(("T* " if index else "") + "(" + escaped + ") Tj")
    operations.append("ET")
    stream = "\n".join(operations).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n")
    start = len(result)
    result.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n")
    result.extend(str(start).encode() + b"\n%%EOF\n")
    return bytes(result)


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class MediaFixture:
    def __init__(self, source: str, transport: str) -> None:
        if transport not in {"tool", "pdf", "web"} or len(source.encode()) > 16000:
            raise ValueError("unsupported owned fixture")
        self.source, self.transport = source, transport
        self.payload = (
            text_pdf(source)
            if transport == "pdf"
            else (
                "<!doctype html><html><body><pre>" + html.escape(source) + "</pre></body></html>"
            ).encode()
            if transport == "web"
            else source.encode()
        )
        self.url: str | None = None
        self.reads = 0
        self.extracted: str | None = None

    @contextmanager
    def serve(self) -> Iterator[None]:
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/bill.html":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(fixture.payload)))
                self.end_headers()
                self.wfile.write(fixture.payload)

            def log_message(self, *args: Any) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.url = f"http://127.0.0.1:{server.server_port}/bill.html"
        try:
            yield
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def read(self) -> str:
        if self.transport == "pdf":
            from pypdf import PdfReader  # type: ignore[import-not-found,unused-ignore]

            reader = PdfReader(io.BytesIO(self.payload))
            if len(reader.pages) != 1:
                raise ValueError("owned PDF page count changed")
            text = reader.pages[0].extract_text()
        elif self.transport == "web":
            if self.url is None:
                raise ValueError("owned HTTP fixture is not running")
            with httpx.Client(trust_env=False, timeout=2, follow_redirects=False) as client:
                response = client.get(self.url)
                response.raise_for_status()
            if response.content != self.payload:
                raise ValueError("owned HTTP payload changed")
            parser = TextOnly()
            parser.feed(response.text)
            text = "".join(parser.parts)
        else:
            text = self.payload.decode()
        if not isinstance(text, str) or normalized(text) != normalized(self.source):
            raise ValueError("transport changed source semantics")
        self.reads += 1
        self.extracted = text
        return text
