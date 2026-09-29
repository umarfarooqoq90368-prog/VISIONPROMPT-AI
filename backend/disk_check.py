import os, shutil
total, used, free = shutil.disk_usage("/")
print(f"Total disk: {total/(1024**4):.1f} TB")
print(f"Free disk: {free/(1024**4):.1f} GB")
