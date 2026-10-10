import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_FAILURE_EXIT_CODE: Final = 17


@dataclass(frozen=True, slots=True, kw_only=True)
class LabShell:
    directory: Path
    project: Path
    home: Path
    trace_file: Path
    environment: dict[str, str]

    def run(
        self,
        arguments: tuple[str, ...],
        *,
        fail_call: int = 0,
        exit_code: int = DEFAULT_FAILURE_EXIT_CODE,
        failures: tuple[str, ...] = (),
        reset_trace: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if reset_trace:
            self.trace_file.write_text("", encoding="utf-8")
        environment = dict(self.environment)
        environment.update(
            LAB_TEST_FAIL_CALL=str(fail_call),
            LAB_TEST_FAIL_CODE=str(exit_code),
            LAB_TEST_FAILURES=",".join(failures),
        )
        return subprocess.run(
            (str(self.project / "scripts/lab.sh"), *arguments),
            cwd=self.directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def commands(self) -> list[list[str]]:
        return [shlex.split(line) for line in self.trace_file.read_text(encoding="utf-8").splitlines()]

    @property
    def provider_directory(self) -> Path:
        return self.directory / "provider"

    def pid(self, name: str) -> int:
        return int((self.provider_directory / name).read_text(encoding="utf-8"))


def tool_source(name: str) -> str:
    return (
        f"name = {name!r}\n"
        """import os
import plistlib
import shlex
import sys
import time
from pathlib import Path

arguments = [name, *sys.argv[1:]]
trace = Path(os.environ["LAB_TEST_TRACE"])
with trace.open("a") as stream:
    stream.write(shlex.join(arguments) + "\\n")
exit_code = int(os.environ["LAB_TEST_FAIL_CODE"])
if len(trace.read_text().splitlines()) == int(os.environ["LAB_TEST_FAIL_CALL"]):
    raise SystemExit(exit_code)
provider = Path(os.environ["LAB_TEST_PROVIDER"])
failures = os.environ["LAB_TEST_FAILURES"].split(",")
vm_directory = Path(os.environ["HOME"]) / ".lima/agent-research"
vm_status = provider / "vm-status"

def fail(operation):
    if operation in failures:
        raise SystemExit(exit_code)

if name == "limactl" and arguments[1:3] == ["list", "--format"]:
    if vm_status.is_file():
        print(vm_status.read_text())
    elif vm_directory.is_dir():
        print("Stopped")
    raise SystemExit(0)
if name == "limactl" and arguments[1] == "start":
    time.sleep(float(os.environ["LAB_TEST_VM_START_DELAY"]))
    vm_directory.mkdir(parents=True, exist_ok=True)
    (vm_directory / "ssh.config").write_text("# fixture SSH configuration\\n")
    vm_status.write_text("Running")
    fail("vm-start")
if name == "limactl" and arguments[1] == "stop":
    fail("vm-stop")
    vm_status.write_text("Stopped")
if name == "launchctl":
    action = arguments[1]
    if action == "bootstrap":
        agent = plistlib.loads(Path(arguments[-1]).read_bytes())
        service = agent["Label"].rsplit(".", 1)[1]
        counter = provider / "pid-counter"
        pid = int(counter.read_text()) + 1 if counter.is_file() else 1000
        counter.write_text(str(pid))
        (provider / service).write_text(str(pid))
        fail("bootstrap-" + service)
        raise SystemExit(0)
    service = arguments[-1].rsplit(".", 1)[1]
    job = provider / service
    if action == "print":
        fail("inspect-" + service)
        if not job.is_file():
            print('Could not find service "' + service + '"', file=sys.stderr)
            raise SystemExit(113)
        print("service = {\\n  pid = " + job.read_text() + "\\n}")
        raise SystemExit(0)
    if action == "bootout":
        fail("bootout-" + service)
        job.unlink(missing_ok=True)
        raise SystemExit(0)
if name == "curl" or (name == "limactl" and "curl" in arguments):
    service = "ollama" if name == "curl" else "ollama-tunnel"
    if not (provider / service).is_file() and not (provider / "external-api").is_file():
        raise SystemExit(7)
    print('{"version": "fixture-version"}')
    raise SystemExit(0)
print(shlex.join(arguments))
"""
    )


def build_lab_shell(directory: Path) -> LabShell:
    project = directory / "project with space"
    home = directory / "home"
    home.mkdir()
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[2]
    shutil.copy2(source / "scripts/lab.sh", scripts / "lab.sh")
    shutil.copytree(source / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__"))
    tools = directory / "bin"
    tools.mkdir()
    for name in ("limactl", "ollama", "launchctl", "curl"):
        executable = tools / name
        executable.write_text(f"#!{sys.executable}\n{tool_source(name)}", encoding="utf-8")
        executable.chmod(0o755)
    (tools / "python3").symlink_to(sys.executable)
    trace_file = directory / "commands"
    trace_file.write_text("", encoding="utf-8")
    provider_directory = directory / "provider"
    provider_directory.mkdir()
    environment = dict(os.environ)
    environment.update(
        HOME=str(home),
        PATH=f"{tools}:{os.environ['PATH']}",
        LAB_TEST_TRACE=str(trace_file),
        LAB_TEST_PROVIDER=str(provider_directory),
        LAB_TEST_VM_START_DELAY="0",
    )
    return LabShell(directory=directory, project=project, home=home, trace_file=trace_file, environment=environment)
