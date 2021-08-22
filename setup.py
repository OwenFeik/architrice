import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="architrice",
    version="0.0.4",
    url="https://github.com/OwenFeik/architrice.git",
    author="Owen Feik",
    author_email="owen.h.feik@gmail.com",
    description="Utility to sync MtG decklists with online sources.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    download_url="https://github.com/OwenFeik/architrice/archive/refs/tags/0.0.4.tar.gz",
    install_requires=["requests", "bs4"],
)
