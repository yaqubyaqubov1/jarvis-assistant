from tools.paths import resolve_path

def verify(tool_name, args, result):
    """Return (verified, message). Conservative: only verify actions we can inspect reliably."""
    try:
        if tool_name == "create_folder":
            ok = resolve_path(args["path"]).exists()
            return ok, "folder exists" if ok else "folder was not found after creation"
        if tool_name == "write_text_file":
            ok = resolve_path(args["path"]).is_file()
            return ok, "file exists" if ok else "file was not found after writing"
        if tool_name == "copy_file":
            ok = resolve_path(args["destination"]).exists()
            return ok, "copy exists" if ok else "destination was not found"
        if tool_name == "move_file":
            ok = resolve_path(args["destination"]).exists() and not resolve_path(args["source"]).exists()
            return ok, "move verified" if ok else "move could not be verified"
        if tool_name == "open_application":
            return True, "launch request completed"
        return True, "no additional verification required"
    except Exception as exc:
        return False, f"verification failed: {exc}"
