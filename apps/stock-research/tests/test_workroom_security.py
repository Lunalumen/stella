import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('private_workroom_server',ROOT/'workroom'/'server.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PrivateWorkroomTests(unittest.TestCase):
 def setUp(self):
  self.server=module.PrivateServer(0)
  self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.worker.join()
 def request(self,path='/',method='GET',headers=None,body=None):
  connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  connection.request(method,path,body=body,headers=headers or {})
  response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read());connection.close();return result
 def login(self):
  code,headers,_=self.request('/session','POST',{'Origin':self.server.origin,'Content-Type':'application/json'},json.dumps({'key':self.server.key}))
  self.assertEqual(code,204);return headers['Set-Cookie'].split(';',1)[0]
 def test_loopback_and_no_unauthenticated_assets(self):
  self.assertEqual(self.server.server_address[0],'127.0.0.1')
  self.assertIn('잠겨'.encode(),self.request()[2])
  for path in ['/app.js','/chart.html','/market.js','/style.css']:
   self.assertEqual(self.request(path)[0],401)
 def test_authentication_cookie_and_static_allowlist(self):
  cookie=self.login()
  code,headers,body=self.request('/',headers={'Cookie':cookie})
  self.assertEqual(code,200);self.assertIn(b'MARKET WINDOW',body)
  self.assertIn('no-store',headers['Cache-Control']);self.assertIn('nosniff',headers['X-Content-Type-Options'])
  self.assertIn("frame-ancestors 'self'",headers['Content-Security-Policy'])
  for path in ['/../private/workroom-access.json','/%2e%2e/private/','/server.py','/README.md','/start.ps1','//private/','/private/','/']:
   if path!='/':self.assertEqual(self.request(path,headers={'Cookie':cookie})[0],404)
  _,h,_=self.request('/session','POST',{'Origin':self.server.origin,'Content-Type':'application/json'},json.dumps({'key':self.server.key}))
  self.assertIn('HttpOnly',h['Set-Cookie']);self.assertIn('SameSite=Strict',h['Set-Cookie'])
 def test_host_origin_and_cross_site_requests(self):
  cookie=self.login()
  self.assertEqual(self.request('/',headers={'Host':'attacker.example','Cookie':cookie})[0],403)
  self.assertEqual(self.request('/',headers={'Sec-Fetch-Site':'cross-site','Cookie':cookie})[0],403)
  self.assertEqual(self.request('/session','POST',{'Origin':'https://attacker.example','Content-Type':'application/json'},'{}')[0],403)
  self.assertEqual(self.request('/session','POST',{'Content-Type':'application/json'},'{}')[0],403)
 def test_expiry_logout_and_invalid_key(self):
  cookie=self.login();token=cookie.split('=',1)[1]
  self.server.sessions[token]=time.monotonic()-1
  self.assertEqual(self.request('/chart.html',headers={'Cookie':cookie})[0],401)
  cookie=self.login()
  self.assertEqual(self.request('/logout','POST',{'Cookie':cookie,'Origin':self.server.origin,'Content-Type':'application/json'},'{}')[0],204)
  self.assertEqual(self.request('/app.js',headers={'Cookie':cookie})[0],401)
  self.assertEqual(self.request('/session','POST',{'Origin':self.server.origin,'Content-Type':'application/json'},'{"key":"wrong"}')[0],401)
  self.assertEqual(self.request('/session','POST',{'Origin':self.server.origin,'Content-Type':'application/json'},json.dumps({'key':'잘못된 키'}))[0],401)
 def test_body_limit_and_rate_limit(self):
  h={'Origin':self.server.origin,'Content-Type':'application/json'}
  self.assertEqual(self.request('/session','POST',h,'x'*513)[0],400)
  for _ in range(10):self.assertEqual(self.request('/session','POST',h,'{}')[0],401)
  self.assertEqual(self.request('/session','POST',h,'{}')[0],429)
 def test_symlink_escape_is_not_served(self):
  with tempfile.TemporaryDirectory() as folder:
   self.server.root=Path(folder).resolve()
   try:self.server.root.joinpath('index.html').symlink_to(ROOT/'README.md')
   except OSError:self.skipTest('symlink permission unavailable')
   self.assertEqual(self.request('/',headers={'Cookie':self.login()})[0],404)

if __name__=='__main__':unittest.main()
