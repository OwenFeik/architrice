import setuptools

with open("architrice/version.py", "r") as f:
    for line in f:
        if "__version__" in line:
            version = line.split("=")[1].strip().replace('"', "")

with open("README.md", "r") as f:
    long_description = f.read()

GITHUB_URL = "https://github.com/OwenFeik/architrice"

setuptools.setup(
    name="architrice",
    version=version,
    url=GITHUB_URL,
    author="Owen Feik",
    author_email="owen.h.feik@gmail.com",
    description="Utility to sync MtG decklists with online sources.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    download_url=f"{GITHUB_URL}/archive/refs/tags/{version}.tar.gz",
    install_requires=["requests", "bs4"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 3 - Alpha",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.7",
)
