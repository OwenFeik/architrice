import setuptools

setuptools.setup(
    name="architrice",
    version="0.0.1",
    url="https://github.com/OwenFeik/architrice.git",
    author="Owen Feik",
    author_email="owen.h.feik@gmail.com",
    description="Utility to download Archidekt decklists for local use.",
    packages=setuptools.find_packages(),
    download_url="https://github.com/OwenFeik/architrice/archive/refs/tags/0.0.1.tar.gz",
    install_requires=["requests"]
)
