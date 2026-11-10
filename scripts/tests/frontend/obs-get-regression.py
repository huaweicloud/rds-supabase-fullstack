"""Local HTTP fixtures for the documented GET checks; no cloud access."""
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTML = b'<!doctype html><title>release-1</title><script src="/app.js"></script><link rel="stylesheet" href="/app.css"><img src="/image.svg">'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

    def do_GET(self):
        status, mime, body = 200, 'text/html', HTML
        host = self.headers.get('Host', '')
        if self.path == '/' and host.startswith('xml.invalid:'):
            mime, body = 'application/xml', b'<ListBucketResult/>'
        elif self.path == '/bad-mime':
            mime = 'application/octet-stream'
        elif self.path == '/error-page':
            body = b'<!doctype html><title>Service Error</title>'
        elif self.path == '/redirect':
            status, body = 302, b''
        elif self.path == '/app.js':
            mime, body = 'application/javascript', b'console.log("release-1");'
        elif self.path == '/app.css':
            mime, body = 'text/css', b'body { color: black; }'
        elif self.path == '/image.svg':
            mime, body = 'image/svg+xml', b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        elif self.path not in ('/', '/attachment', '/bad-mime', '/error-page'):
            status, body = 404, b'Not found'
        self.send_response(status)
        self.send_header('Content-Type', mime)
        if self.path == '/attachment':
            self.send_header('Content-Disposition', 'attachment')
        if self.path == '/redirect':
            self.send_header('Location', '/attachment')
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_port
    base = f'http://127.0.0.1:{port}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            def request(url, *extra):
                headers, body = Path(tmp)/'headers', Path(tmp)/'body'
                result = subprocess.run([
                    'curl', '--noproxy', '*', '--silent', '--show-error',
                    '--location', '--max-redirs', '5', '--max-time', '5',
                    '--dump-header', str(headers), '--output', str(body),
                    '--write-out', '%{http_code}\n%{url_effective}', *extra, url,
                ], capture_output=True, text=True)
                blocks = headers.read_text().strip().split('\n\n')
                final = blocks[-1].lower() if blocks else ''
                return result, final, body.read_bytes() if body.exists() else b''

            # These are fixture expectations, not a production acceptance engine.
            # Inspect the same final headers/body/URL required by deployment.md.
            for path, mime, expected in [('/', 'text/html', HTML),
                                        ('/app.js', 'application/javascript', b'console.log'),
                                        ('/app.css', 'text/css', b'body {'),
                                        ('/image.svg', 'image/svg+xml', b'<svg')]:
                result, headers, body = request(base+path)
                assert result.returncode == 0 and result.stdout.startswith('200\n')
                assert f'content-type: {mime}' in headers and expected in body
                assert 'attachment' not in headers
                print('PASS valid GET', path)
            result, headers, _ = request(base+'/attachment', '--head')
            assert result.returncode == 0 and 'attachment' not in headers
            print('PASS HEAD blind spot reproduced')
            for path in ['/attachment', '/redirect']:
                result, headers, body = request(base+path)
                assert 'content-disposition: attachment' in headers and body == HTML
                assert result.stdout.endswith('/attachment')
                print('PASS reject GET attachment', path)
            result, headers, body = request(f'http://xml.invalid:{port}/', '--resolve', f'xml.invalid:{port}:127.0.0.1')
            assert result.stdout.startswith('200\n') and b'ListBucketResult' in body
            assert 'application/xml' in headers
            print('PASS reject root XML')
            _, headers, _ = request(base+'/bad-mime')
            assert 'application/octet-stream' in headers
            print('PASS reject wrong MIME')
            result, _, body = request(base+'/error-page')
            assert result.stdout.startswith('200\n') and body != HTML
            print('PASS reject 200 error page')
            for path in ['/missing.js', '/api/unknown', '/account/deep']:
                result, _, body = request(base+path)
                assert result.stdout.startswith('404\n') and body != HTML
                print('PASS negative 404 (deep link remains failed)', path)
            url = f'http://site.invalid:{port}/'
            result, _, body = request(url, '--resolve', f'site.invalid:{port}:127.0.0.1')
            assert result.returncode == 0 and body == HTML
            result, _, _ = request(url)
            assert result.returncode == 6, result.stderr
            print('PASS resolve diagnostic succeeds, normal DNS fails')
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()
