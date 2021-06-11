# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\Users\\Andy\\Dropbox\\Projects\\2021_FRC\\py36venv\\Lib\\site-packages\\shiboken2', 'C:\\Users\\Andy\\Dropbox\\Projects\\2021_FRC\\py36venv\\TimeClock2'],
             binaries=[],
             datas=[('form.ui', '.'), ('4418.png', '.')],
             hiddenimports=['PySide2.QtXml'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='main',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
