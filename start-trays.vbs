' start-trays.vbs - launch all tray indicators silently via pythonw (no consoles).
Set sh = CreateObject("WScript.Shell")
base = "C:\Users\AustinCrozier\Dev\tray-indicators\"
pyw  = "C:\Users\AustinCrozier\AppData\Local\Programs\Python\Python311\pythonw.exe"
sh.Run """" & pyw & """ """ & base & "vault_sync.py""", 0, False
sh.Run """" & pyw & """ """ & base & "dirty_repos_light.py""", 0, False
sh.Run """" & pyw & """ """ & base & "clockon_light.py""", 0, False
sh.Run """" & pyw & """ """ & base & "homestead_light.py""", 0, False
