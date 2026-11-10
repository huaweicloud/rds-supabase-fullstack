"""Exercise real curl GETs against an isolated HTTP fixture."""
import http.server
import pathlib
import subprocess
import tempfile
import threading

SCRIPT = pathlib.Path(__file__).resolve().parents[3] / 'skills/huaweicloud-supabase/rds-supabase-frontend/scripts/probe-suite.sh'
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/ok')
        else:
            self.send_response(403 if self.path == '/denied' else 200)
            self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html>version-fixture</html>')
    def log_message(self, *args):
        pass
with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server, tempfile.TemporaryDirectory() as temp:
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    def run(name, *paths):
        return subprocess.run(['bash', str(SCRIPT), str(pathlib.Path(temp)/name), *[base+p for p in paths]], capture_output=True)
    assert run('ok', '/ok', '/redirect').returncode == 0
    assert '302' in (pathlib.Path(temp)/'ok/2.headers').read_text()
    assert (pathlib.Path(temp)/'ok/2.body').read_bytes() == b'<html>version-fixture</html>'
    assert run('bad', '/ok', '/denied').returncode == 1
    assert run('ok', '/ok').returncode == 2  # immutable evidence
    assert (pathlib.Path(temp)/'ok').stat().st_mode & 0o777 == 0o700
    server.shutdown()
print('PASS parallel GET, redirect evidence, HTTP failure, private immutable output')
