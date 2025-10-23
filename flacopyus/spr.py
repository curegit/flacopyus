import shutil


def which(cmd: str) -> str:
    match shutil.which(cmd):
        case None:
            raise RuntimeError(f"Command not found: '{cmd}'")
        case path:
            return path
