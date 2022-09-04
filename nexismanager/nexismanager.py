import subprocess, pathlib, sys, dataclasses, typing

class WorkspaceManager:

	def __init__(self, server:str, *, username:str, password:str, mount_root:str="/Volumes"):
		"""Create a Nexis workspace manager"""

		# Store credentials
		self.__credentials = {
			"server": server,
			"username": username,
			"password": password
		}

		# Set and validate mount root
		self._mount_root = pathlib.Path(mount_root)
		if not self._mount_root.is_dir():
			raise FileNotFoundError(f"Mount point {self._mount_root} is not a valid directory")

		# Create new mounts dict
		self._mounts = set()
	
	def __del__(self):
		"""Clean up stray mounts"""
		
		for ws in self._mounts:
			print(f"Unmounting stray workspace {ws}...", file=sys.stderr)
			self._unmount_workspace(ws)
	
	@property
	def username(self) -> str:
		"""The current username"""
		return self.__credentials.get("username")
	
	@property
	def server(self) -> str:
		"""The current server"""
		return self.__credentials.get("server")

	def build_workspace_path(self, workspace:str, mount_root:typing.Union[str,pathlib.Path,None]=None) -> pathlib.Path:
		"""Build a unique mount point path"""

		mount_root = mount_root or self._mount_root
		path_candidate = pathlib.Path(mount_root, workspace)
		
		# Avoid anything weird
		if path_candidate.exists():
			idx = 0
			while path_candidate.exists():
				idx += 1
				path_candidate = pathlib.Path(mount_root, workspace + "_" + str(idx))
		
		return path_candidate

	def mount(self, workspace:str, read_only:bool=True) -> "Workspace":
		"""Mount a workspace"""

		ws = Workspace(
			manager=self,
			workspace=str(workspace),
			mount_point=self.build_workspace_path(workspace),
			read_only=bool(read_only)
		)

		self._mount_workspace(ws)
		return ws
	
	def _mount_workspace(self, ws:"Workspace"):
		"""Actually mount a workspace"""

		if ws in self._mounts:
			print(f"Already mounted: {ws}", file=sys.stderr)
			return

		options = ["-o","rdonly"] if ws.read_only else []

		cmd_mount = [
			"mount_avid",
			*options,
			f"-U", f"{self.__credentials.get('username')}:{self.__credentials.get('password')}",
			f"{self.__credentials.get('server')}:{ws.workspace}",
			str(ws.mount)
		]

		proc = subprocess.run(cmd_mount, capture_output=True)
		if proc.returncode != 0 or not ws.mount.is_mount():
			raise OSError(f"Could not mount {ws.workspace} to {ws.mount} (Err {proc.returncode}: {proc.stderr.decode('latin-1').strip()})")
		
		self._mounts.add(ws)

	def _unmount_workspace(self, ws:"Workspace"):
		"""Actually unmount a workspace"""

		if ws not in self._mounts:
			raise ValueError(f"This workspace is not managed by this workspace manager")
		
		if not ws.mount.is_mount():
			print(f"Already unmounted: {ws}", file=sys.stderr)
			self._mounts.remove(ws)
			return

		cmd_unmount = [
			"umount",
			str(ws.mount)
		]
		proc = subprocess.run(cmd_unmount, capture_output=True)
		
		if proc.returncode != 0 or ws.mount.is_mount():
			raise OSError(f"Could not unmount {ws.workspace} from {ws.mount} (Err {proc.returncode}: {proc.stderr.decode('latin-1').strip()})")
		else:
			self._mounts.remove(ws)

@dataclasses.dataclass(frozen=True)
class Workspace:
	"""A mounted Nexis Workspace"""

	manager:WorkspaceManager
	"""The `WorkspaceManager` responsible for this workspace"""

	workspace:str
	"""The name of this Nexis workspace"""

	mount_point:pathlib.Path
	"""The mount point in the filesystem for this workspace"""

	read_only:bool
	"""Indicates if the workspace is mounted as read only"""

	def __enter__(self):
		"""Context manager"""
		return self

	def __exit__(self, *args, **kwargs):
		"""Cleanup"""
		try:
			self.manager._unmount_workspace(self)
		except Exception as e:
			print(f"Unable to close {self}: {e}", file=sys.stderr)