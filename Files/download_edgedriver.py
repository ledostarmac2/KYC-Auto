import os
import re
import shutil
import tempfile
import urllib.request
import zipfile


EDGEDRIVER_ZIP_NAME = "edgedriver_win64.zip"


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def find_edge_version() -> str | None:
    candidate_roots = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application",
        r"C:\Program Files\Microsoft\Edge\Application",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application"),
    ]
    versions: list[str] = []
    for root in candidate_roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", name):
                versions.append(name)

    if not versions:
        return None
    return sorted(versions, key=version_tuple)[-1]


def download_edgedriver(output_path: str = "msedgedriver.exe") -> str:
    edge_version = find_edge_version()
    if not edge_version:
        raise RuntimeError("Microsoft Edge was not found, so EdgeDriver could not be downloaded.")

    url = f"https://msedgedriver.microsoft.com/{edge_version}/{EDGEDRIVER_ZIP_NAME}"
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, EDGEDRIVER_ZIP_NAME)
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as archive:
            driver_member = next(
                (name for name in archive.namelist() if name.lower().endswith("msedgedriver.exe")),
                None,
            )
            if driver_member is None:
                raise RuntimeError("Downloaded EdgeDriver package did not contain msedgedriver.exe.")
            with archive.open(driver_member) as source, open(output_path, "wb") as destination:
                shutil.copyfileobj(source, destination)
    return edge_version


if __name__ == "__main__":
    version = download_edgedriver()
    print(f"Downloaded Microsoft Edge WebDriver {version}")
