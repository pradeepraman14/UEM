"""
Windows Update Agent (WUA) integration.
Uses COM interface to scan for, list, and install Windows patches.
"""
import platform
import subprocess
from typing import Any

from agent.src.logger import get_logger

logger = get_logger(__name__)


def scan_missing_patches() -> list[dict[str, Any]]:
    """Scan for missing Windows patches using Windows Update Agent COM API."""
    if platform.system() != "Windows":
        return []

    try:
        import win32com.client
        update_session = win32com.client.Dispatch("Microsoft.Update.Session")
        searcher = update_session.CreateUpdateSearcher()

        logger.info("Scanning for missing Windows updates...")
        result = searcher.Search("IsInstalled=0 AND IsHidden=0")

        patches = []
        for update in result.Updates:
            kb_ids = []
            if hasattr(update, "KBArticleIDs"):
                kb_ids = [str(kb) for kb in update.KBArticleIDs]

            severity_map = {0: None, 1: "low", 2: "moderate", 3: "important", 4: "critical"}
            msrc_map = {0: None, 1: "low", 2: "moderate", 3: "important", 4: "critical"}

            patches.append({
                "title": update.Title,
                "kb_article_id": f"KB{kb_ids[0]}" if kb_ids else None,
                "description": update.Description,
                "severity": msrc_map.get(update.MsrcSeverity, None),
                "patch_type": "security" if update.AutoSelectOnWebSites else "quality",
                "reboot_required": update.InstallationBehavior.RebootBehavior > 0,
                "size_bytes": sum(f.Size for f in update.DownloadContents if hasattr(f, "Size")),
                "identity": update.Identity.UpdateID,
            })

        logger.info("Patch scan complete", missing_count=len(patches))
        return patches

    except Exception as e:
        logger.error("WUA scan failed", error=str(e))
        return _fallback_powershell_scan()


def install_patches(kb_ids: list[str] | None = None, install_all: bool = False) -> dict[str, Any]:
    """Install Windows patches. If kb_ids is None and install_all=True, install all approved."""
    if platform.system() != "Windows":
        return {"success": True, "message": "Patch install skipped (non-Windows)", "installed": []}

    try:
        import win32com.client

        update_session = win32com.client.Dispatch("Microsoft.Update.Session")
        searcher = update_session.CreateUpdateSearcher()
        result = searcher.Search("IsInstalled=0 AND IsHidden=0")

        to_install = win32com.client.Dispatch("Microsoft.Update.UpdateColl")
        installed = []

        for update in result.Updates:
            kb_list = [str(kb) for kb in update.KBArticleIDs]
            if install_all or any(f"KB{kb}" in (kb_ids or []) or kb in (kb_ids or []) for kb in kb_list):
                to_install.Add(update)

        if to_install.Count == 0:
            return {"success": True, "message": "No patches to install", "installed": []}

        # Download
        downloader = update_session.CreateUpdateDownloader()
        downloader.Updates = to_install
        logger.info("Downloading patches", count=to_install.Count)
        downloader.Download()

        # Install
        installer = update_session.CreateUpdateInstaller()
        installer.Updates = to_install
        logger.info("Installing patches", count=to_install.Count)
        install_result = installer.Install()

        for i in range(to_install.Count):
            update = to_install.Item(i)
            kb_list = [str(kb) for kb in update.KBArticleIDs]
            code = install_result.GetUpdateResult(i).ResultCode
            installed.append({
                "title": update.Title,
                "kb_id": f"KB{kb_list[0]}" if kb_list else None,
                "result_code": code,  # 2=Success, 3=SucceededWithErrors, 4=Failed, 5=Aborted
                "success": code in (2, 3),
                "reboot_required": install_result.GetUpdateResult(i).RebootRequired,
            })

        reboot_required = install_result.RebootRequired
        return {
            "success": True,
            "message": f"Installed {len(installed)} patches",
            "installed": installed,
            "reboot_required": reboot_required,
        }

    except Exception as e:
        logger.error("Patch installation failed", error=str(e))
        return {"success": False, "message": str(e), "installed": []}


def _fallback_powershell_scan() -> list[dict[str, Any]]:
    """Fallback: use PSWindowsUpdate module if WUA COM fails."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-WindowsUpdate -AcceptAll | Select-Object KB, Title, Size | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            updates = json.loads(result.stdout)
            if isinstance(updates, dict):
                updates = [updates]
            return [
                {
                    "title": u.get("Title"),
                    "kb_article_id": u.get("KB"),
                    "patch_type": "security",
                    "reboot_required": False,
                    "size_bytes": None,
                }
                for u in updates
            ]
    except Exception:
        pass
    return []
