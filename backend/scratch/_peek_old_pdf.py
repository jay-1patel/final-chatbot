import subprocess

text = subprocess.check_output(
    ["git", "show", "fe07299^:backend/services/auto_bifurcator.py"]
).decode("utf-8")
i = text.find('if ext == ".pdf"')
print(text[i : i + 1500])
