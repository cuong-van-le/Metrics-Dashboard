import subprocess  # nosec B404
import sys
import zipfile
from pathlib import Path


def package_lambda():
    transform_dir = Path("transform")
    output_file = Path("lambda_package.zip")

    if not transform_dir.exists():
        print(f"Error: {transform_dir} directory not found")
        sys.exit(1)

    requirements_file = transform_dir / "requirements.txt"

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in transform_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                if file_path.name == "requirements.txt":
                    continue
                arcname = file_path.relative_to(transform_dir)
                zip_file.write(file_path, arcname)
                print(f"  Added: {arcname}")

        if requirements_file.exists():
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                try:
                    subprocess.run(  # nosec B603
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            "-r",
                            str(requirements_file),
                            "-t",
                            str(temp_path),
                            "--quiet",
                            "--no-cache-dir",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                    added_count = 0
                    for file_path in temp_path.rglob("*"):
                        if file_path.is_file():
                            if (
                                "__pycache__" in str(file_path)
                                or file_path.suffix == ".pyc"
                            ):
                                continue
                            arcname = file_path.relative_to(temp_path)
                            zip_file.write(file_path, arcname)
                            added_count += 1
                except subprocess.CalledProcessError as e:
                    print(e)
                    sys.exit(1)


if __name__ == "__main__":
    package_lambda()
