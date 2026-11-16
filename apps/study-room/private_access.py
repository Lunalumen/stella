"""Windows account-bound private access. Keys are DPAPI encrypted, outside OneDrive."""
import ctypes,json,os,secrets,time
from ctypes import wintypes
from pathlib import Path

def state_dir():
    root=os.environ.get('MYEONGWOL_STATE_PATH')
    return Path(root) if root else Path(os.environ['LOCALAPPDATA'])/'MyeongwolStudy'

class Blob(ctypes.Structure):
    _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]

def crypt(data,protect):
    if os.name!='nt':
        raise RuntimeError('개인용 잠금은 이 Windows 계정에서만 실행할 수 있습니다.')
    buffer=(ctypes.c_ubyte*len(data)).from_buffer_copy(data)
    source=Blob(len(data),buffer);target=Blob()
    dll=ctypes.WinDLL('crypt32',use_last_error=True)
    function=dll.CryptProtectData if protect else dll.CryptUnprotectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.pbData,target.cbData)
    finally:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
        kernel.LocalFree(ctypes.cast(target.pbData,ctypes.c_void_p))

def load_access_key():
    directory=state_dir();directory.mkdir(parents=True,exist_ok=True)
    file=directory/'access-key.dpapi'
    if not file.exists():
        encrypted=crypt(secrets.token_urlsafe(48).encode(),True)
        try:
            with file.open('xb') as stream:stream.write(encrypted)
        except FileExistsError:
            pass
    return crypt(file.read_bytes(),False).decode('ascii')

def launch_url(port=8765):
    load_access_key()
    ticket=secrets.token_urlsafe(48)
    directory=state_dir()
    temp=directory/('ticket-'+secrets.token_hex(8)+'.tmp')
    temp.write_text(json.dumps({'ticket':ticket,'expires':time.time()+120}),encoding='utf8')
    os.replace(temp,directory/'launch-ticket.json')
    return f'http://127.0.0.1:{port}/unlock?ticket={ticket}'

if __name__=='__main__':
    print(launch_url())
