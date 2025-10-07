import os

# Root directory to start searching from
ROOT_DIR = r"C:\Users\int10281\Desktop\Github\Friday - Copy"

# File extensions to include
INCLUDE_EXTENSIONS = {'.py', '.js', '.css', '.html', '.txt'}

# Output file where combined code will be saved
OUTPUT_FILE = os.path.join(ROOT_DIR, "all_code_snippets.txt")

def should_include(file_name):
    return os.path.splitext(file_name)[1] in INCLUDE_EXTENSIONS

def copy_code_snippets():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
            # Exclude venv folder from traversal
            if 'venv' in dirnames:
                dirnames.remove('venv')
            if 'KMS' in dirnames:
                dirnames.remove('KMS')
            if '__pycache__' in dirnames:
                dirnames.remove('__pycache__')
            if 'conversations' in dirnames:
                dirnames.remove('conversations')
            # if 'copy_utils.py' in filenames:
            #     filenames.remove('copy_utils.py')
            # if 'agent.py' in filenames:
            #     filenames.remove('agents.py')

            for filename in filenames:
                if should_include(filename):
                    file_path = os.path.join(dirpath, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            outfile.write(f"\n\n----- File: {file_path} -----\n")
                            outfile.write(content)
                    except Exception as e:
                        print(f"Could not read {file_path}: {e}")

    print(f"\n✅ Code snippets copied to: {OUTPUT_FILE}")

if __name__ == "__main__":
    copy_code_snippets()
