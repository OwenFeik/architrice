import os


COMMAND = (
    "powershell -command "
    "\"(New-Object -ComObject WScript.Shell)"
    ".CreateShortcut(\"\"{}\"\").TargetPath\""
)

PATHS = [
    "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
    # os.path.join(os.getenv("USERPROFILE"), "Start Menu", "Programs")
]
PATHS = PATHS + [os.path.join(path, "Cockatrice") for path in PATHS]

for path in PATHS:
    if os.path.isfile((link := os.path.join(path, "Cockatrice.lnk"))):
        cmd = COMMAND.format(link)
        print(cmd)
        print(os.system(cmd))
