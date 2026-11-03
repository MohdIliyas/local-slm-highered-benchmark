"""A fake Ollama server for testing the pipeline without models.

It imitates the HTTP API (streaming /api/generate, /api/ps, /api/tags,
/api/show, /api/version) and returns canned, task-shaped answers. Outputs are
NOT model behaviour; this only proves the plumbing works end to end.
"""
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = ["llama3.2:3b-instruct-q4_K_M", "llama3.2:3b-instruct-q8_0",
          "qwen2.5:7b-instruct-q4_K_M", "qwen2.5:7b-instruct-q8_0"]
LOADED = {}


def answer(model, prompt):
    sloppy = "llama" in model
    if "Syllabus Text:" in prompt:
        body = prompt.split("Syllabus Text:")[1]
        code = re.search(r"\b([A-Z]{2,4})[ -]?(\d{3})\b", body)
        weights = [w for w in re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", body)]
        w = [{"category": f"Item {i}", "weight_percent": (f"{x}%" if sloppy else float(x))} for i, x in enumerate(weights)]
        obj = {"course_code": f"{code.group(1)} {code.group(2)}" if code else "", "instructor_name": "Unknown",
               "office_hours": "TBA", "grading_breakdown": w, "has_accessibility_statement": "ccommodation" in body}
        return ("Here is the extracted JSON:\n" if sloppy else "") + json.dumps(obj)
    if "Policy Text:" in prompt:
        body = prompt.split("Policy Text:")[1].strip()
        sents = re.split(r"(?<=\.)\s+", body)[:3]
        pre = "Here are three bullet points summarizing the policy:\n\n" if sloppy else ""
        return pre + "\n".join(f"- {s}" for s in sents)
    if "Categorize the following" in prompt:
        t = prompt.lower()
        for kw, lab in [("caption", "Accessibility/Captions"), ("screen reader", "Accessibility/Captions"),
                        ("lockdown", "Online Proctoring"), ("webcam", "Online Proctoring"),
                        ("password", "Login/Account Lockout"), ("grade", "Grade Disputes"),
                        ("register", "Course Enrollment"), ("exam", "Exam Rescheduling"),
                        ("blackboard", "LMS Access")]:
            if kw in t.split("ticket:")[-1]:
                return lab + ("." if sloppy else "")
        return "General Inquiries"
    if "Student Inquiry:" in prompt:
        tail = "\nYou can also call us at (216) 555-0100." if sloppy else ""
        return ("Subject: Re: Your request\n\nDear Student,\n\nThank you for reaching out. Please contact "
                "[relevant office] and include [your student ID]." + tail + "\n\nSincerely,\nAcademic Support Services")
    return "ready"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _chunk(self, text):
        b = text.encode()
        self.wfile.write(f"{len(b):X}\r\n".encode() + b + b"\r\n")
        self.wfile.flush()

    def do_GET(self):
        if self.path == "/api/version":
            return self._json({"version": "0.0.0-mock"})
        if self.path == "/api/tags":
            return self._json({"models": [{"name": m, "model": m, "digest": "mock" + str(i)} for i, m in enumerate(MODELS)]})
        if self.path == "/api/ps":
            return self._json({"models": [{"name": m, "size": s, "size_vram": 0} for m, s in LOADED.items()]})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            return self._json({"details": {"quantization_level": req["model"].split("-")[-1]}, "model_info": {}})
        if self.path != "/api/generate":
            return self._json({"error": "not found"}, 404)
        m = req["model"]
        if req.get("keep_alive") == 0 and "prompt" not in req:
            LOADED.pop(m, None)
            return self._json({"done": True})
        cold = m not in LOADED
        LOADED[m] = int((3 if "3b" in m else 7) * (1.1 if "q8" in m else 0.6) * 1e9)
        toks = re.findall(r"\S+\s*|\n", answer(m, req["prompt"]))[: req["options"].get("num_predict", 512)]
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")  # like Ollama's streaming responses
        self.end_headers()
        t0 = time.perf_counter()
        time.sleep(0.003)
        per = 0.0006 if "3b" in m else 0.0012
        for tok in toks:
            time.sleep(per)
            self._chunk(json.dumps({"model": m, "response": tok, "done": False}) + "\n")
        dur = int((time.perf_counter() - t0) * 1e9)
        final = {"model": m, "response": "", "done": True, "total_duration": dur + (2_000_000_000 if cold else 0),
                 "load_duration": 2_000_000_000 if cold else 1_000_000,
                 "prompt_eval_count": len(req["prompt"]) // 4, "prompt_eval_duration": 3_000_000,
                 "eval_count": len(toks), "eval_duration": max(dur - 3_000_000, 1)}
        self._chunk(json.dumps(final) + "\n")
        self.wfile.write(b"0\r\n\r\n")


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # clients closing keep-alive sockets on exit is expected


def serve(port=0):
    """Start the mock server. port=0 lets the OS pick a free port (see srv.server_port)."""
    srv = QuietServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 11500)
    print("mock ollama running; Ctrl-C to stop")
    while True:
        time.sleep(3600)
