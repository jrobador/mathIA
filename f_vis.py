#%%
import os

def display_tree(startpath, indent=''):
    skip_dirs = {'.react-router', 'node_modules', '.git'}
    
    try:
        items = os.listdir(startpath)
    except PermissionError:
        print(f"{indent}├── [Permission Denied]")
        return

    for item in items:
        if item in skip_dirs or item in ('__pycache__', '__init__.py'):
            continue
        path = os.path.join(startpath, item)
        if os.path.isdir(path):
            print(f"{indent}├── {item}/")
            display_tree(path, indent + '    ')
        else:
            print(f"{indent}├── {item}")


if __name__ == "__main__":
    startpath = '.'  # Change this to the directory you want to visualize
    display_tree(startpath)
# %%
