import sys
from nexismanager import WorkspaceManager
from test_credentials import NEXIS_SERVER, USERNAME, PASSWORD


if __name__ == "__main__":

	if len(sys.argv)<2:
		sys.exit(f"Usage: {__file__} workspace_name")

	wm = WorkspaceManager(NEXIS_SERVER, username=USERNAME, password=PASSWORD)

	mountpoint=None

	with wm.mount(sys.argv[1]) as ws_dir:
		mountpoint = ws_dir.mount
		print(f"{ws_dir.workspace} is mounted to {ws_dir.mount}? {mountpoint.is_mount()}")
		input("Waiting...")

	print(f"Now {mountpoint} is not mounted? {mountpoint.is_mount()}")