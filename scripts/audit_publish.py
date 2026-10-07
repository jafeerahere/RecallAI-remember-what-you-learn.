"""Check project/staged files without printing potential secret values."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git','.venv','venv','__pycache__','.pytest_cache','node_modules','.cache',
        'model-cache','model_cache','models','hf-cache','.huggingface'}
PATTERNS = {
    'GitHub credential':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
    'Hugging Face credential':r'\bhf_[A-Za-z0-9]{30,}\b',
    'OpenAI credential':r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}\b',
    'AWS access key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'Google API key':r'\bAIza[A-Za-z0-9_-]{30,}\b',
    'Private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'Credential URL':r'https?://[^\s/@:]+:[^\s/@]+@',
    'Assigned credential':r'(?i)\b(?:api_?key|secret_?key|access_?token|auth_?token|password|passwd|client_?secret)\s*[:=]\s*[\"\']([^\"\'\n]{8,})[\"\']',
}

def audit(paths):
    findings, imports, variables = [], set(), set()
    for path in paths:
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding='utf-8-sig')
        except (UnicodeError,OSError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for label,pattern in PATTERNS.items():
            for match in re.finditer(pattern,content):
                # Deliberate extraction-test passwords and scanner regexes
                # are examples, never deployment credentials.
                if label == 'Assigned credential' and ('example' in match.group(1).lower() or 'placeholder' in match.group(1).lower()):
                    continue
                findings.append({'file':relative,'line':content.count('\n',0,match.start())+1,'kind':label})
        if path.suffix == '.py':
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imports.update(n.name.split('.')[0] for n in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    imports.add(node.module.split('.')[0])
            variables.update(re.findall(r'(?:getenv|environ\.get)\([\"\']([^\"\']+)',content))
    return findings, sorted(imports), sorted(variables)

def main():
    staged = '--staged' in sys.argv
    if staged:
        result = subprocess.run(['git','diff','--cached','--name-only','-z'],cwd=ROOT,capture_output=True,check=True)
        paths = [ROOT/name for name in result.stdout.decode('utf-8').split('\x00') if name]
    else:
        paths = []
        for folder,dirs,files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP]
            paths.extend(Path(folder)/name for name in files)
    findings,imports,variables = audit(paths)
    forbidden = []
    if staged:
        for path in paths:
            relative = path.relative_to(ROOT)
            name = relative.name
            if (any(p in SKIP or p in {'artifacts','uploads','temporary-uploads'} for p in relative.parts)
                or (name.startswith('.env') and name != '.env.example')
                or name == 'secrets.toml' or path.suffix.lower() in {'.log','.db','.sqlite3','.pyc','.pem','.key'}
                or relative.as_posix().startswith('data/private/')):
                forbidden.append(relative.as_posix())
    print(json.dumps({'mode':'staged' if staged else 'project','files_checked':len(paths),
        'potential_secret_locations':findings,'forbidden_staged_paths':forbidden,
        'import_roots':imports,'environment_variable_names':variables},indent=2))
    return int(bool(findings or forbidden))

if __name__ == '__main__':
    raise SystemExit(main())
