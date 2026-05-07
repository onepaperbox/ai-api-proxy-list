"""
Read ping_check.py results and update latency values in README.md,
then sort and add emoji for unreachable sites.
"""
import re
import subprocess
import platform
import time
import socket
import urllib.request
import urllib.error

README_PATH = r"i:\Downloads\ai-api-proxy-list\README.md"

with open(README_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Find table
table_start = content.find("| 名称 | 官网 | 支持模型 | 官网延迟 |")
table_end = content.find("\n\n## 📚", table_start)
table_text = content[table_start:table_end]

lines = table_text.split("\n")
header = lines[0] + "\n" + lines[1]

# Parse all data rows
data_lines = []
for line in lines[2:]:
    if line.strip() and line.startswith("|"):
        data_lines.append(line)

print(f"Found {len(data_lines)} rows to test")

def test_domain(domain):
    """Test domain using ping, TCP, and HTTP."""
    # Method 1: Ping
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        timeout_val = "3000" if platform.system().lower() == "windows" else "3"
        result = subprocess.run(
            ["ping", param, "1", timeout_param, timeout_val, domain],
            capture_output=True, text=True, timeout=8
        )
        output = result.stdout + result.stderr
        time_match = re.search(r'时间[=<]\s*(\d+)\s*ms', output, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'time[=<]\s*([\d.]+)\s*ms', output, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'(?:平均|Average|最大|Maximum)\s*[=:]\s*(\d+)\s*ms', output, re.IGNORECASE)
        if result.returncode == 0 and time_match:
            return int(float(time_match.group(1))), True
    except:
        pass

    # Method 2: TCP connect to 443
    try:
        start = time.time()
        sock = socket.create_connection((domain, 443), timeout=5)
        elapsed = int((time.time() - start) * 1000)
        sock.close()
        return elapsed, True
    except:
        pass

    # Method 3: TCP connect to 80
    try:
        start = time.time()
        sock = socket.create_connection((domain, 80), timeout=5)
        elapsed = int((time.time() - start) * 1000)
        sock.close()
        return elapsed, True
    except:
        pass

    # Method 4: HTTP request
    for scheme in ['https', 'http']:
        try:
            start = time.time()
            req = urllib.request.Request(f"{scheme}://{domain}", method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            resp = urllib.request.urlopen(req, timeout=5)
            elapsed = int((time.time() - start) * 1000)
            return elapsed, True
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - start) * 1000)
            return elapsed, True
        except:
            continue

    return None, False


# Process each row: extract domain, test it, update latency
import ssl
new_lines = []
for i, line in enumerate(data_lines):
    # Extract domain from markdown link
    m = re.search(r'\[([^\]]+)\]\(https?://([^\)]+)\)', line)
    if not m:
        new_lines.append(line)
        continue
    
    link_text = m.group(1)
    full_url = m.group(2)
    domain = full_url.split('/')[0].replace('www.', '')
    
    name_part = line.split(" | ")[0]
    # Clean name (remove ❌ if present)
    name_clean = name_part.lstrip("| ").strip()
    while name_clean.startswith("❌"):
        name_clean = name_clean[1:].strip()
    
    latency, ok = test_domain(domain)
    
    if latency is not None:
        latency_str = f"{latency}ms"
        # Rebuild the row
        parts = line.strip().split(" | ")
        if len(parts) >= 4:
            # Reconstruct with clean name and new latency
            link_and_models = " | ".join(parts[1:-1])
            new_line = f"| {name_clean} | {link_and_models} | {latency_str} |"
            new_lines.append(new_line)
            status = "✅"
        else:
            new_lines.append(line)
            status = "?"
    else:
        # Unreachable
        parts = line.strip().split(" | ")
        if len(parts) >= 4:
            link_and_models = " | ".join(parts[1:-1])
            new_line = f"| ❌ {name_clean} | {link_and_models} | 超时 |"
            new_lines.append(new_line)
            status = "❌"
        else:
            new_lines.append(line)
            status = "?"
    
    print(f"{i+1:3d}. {status} {name_clean:<30s} {domain:<35s} {latency if latency else '超时'}ms" + (" " if latency else ""))
    time.sleep(0.05)


# Sort: timed-out entries at bottom, then by latency ascending
def sort_key(line):
    parts = line.strip().split(" | ")
    if len(parts) < 4:
        return (2, 99999)
    latency_str = parts[-1].rstrip("|").strip()
    name = parts[0].lstrip("| ❌").strip()
    if latency_str == "超时":
        return (1, 99999, name)
    try:
        ms = int(latency_str.replace("ms", ""))
        return (0, ms, name)
    except:
        return (2, 99999, name)

data_lines_sorted = sorted(new_lines, key=sort_key)

# Build new table
new_table = header + "\n" + "\n".join(data_lines_sorted)

# Replace in content
new_content = content.replace(table_text, new_table)

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"\n✅ Updated {len(new_lines)} entries. Table sorted with ❌ for unreachable sites.")
