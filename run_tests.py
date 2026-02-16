import subprocess, sys, json

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"c:\Users\shrey\OneDrive\Desktop\Omniscent"
)

# Write stdout + stderr to a json file for safe reading
out = {
    "returncode": result.returncode,
    "stdout": result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout,
    "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
}

with open(r"c:\Users\shrey\OneDrive\Desktop\Omniscent\test_output.json", "w") as f:
    json.dump(out, f, indent=2)

print("Done")
