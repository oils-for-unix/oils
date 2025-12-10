#!/usr/bin/env python3
import http.server
import subprocess
import urllib.parse
import os

# Read token from environment variable
AUTH_TOKEN = os.environ.get('CAUSES_AUTH_TOKEN')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        kind = params.get('kind', [''])[0]
        token = params.get('token', [''])[0]
        if token != AUTH_TOKEN:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return
      
        result = subprocess.run(['./regtest/aports-update-causes.sh', 'update-latest', kind], 
                          capture_output=True, 
                          text=True)
        print(result.stderr)
        print("stdout:")
        print(result.stdout)
        if(result.returncode == 0):    
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f'View the new report at: {result.stdout}'.encode())
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'error occured, exit code: {result.returncode}'.encode())
            
    def log_message(self, format, *args):
        pass

http.server.HTTPServer(('', 8080), Handler).serve_forever()
