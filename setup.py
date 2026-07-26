from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).resolve().parent
REQUIREMENTS = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]


setup(
    name="YuLan-OneSim-Researcher",
    version="1.0.0",
    description="Command-line research workflow for YuLan-OneSim",
    url="https://github.com/Paitesanshi/S-Researcher",
    license="Apache-2.0",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
    ],
    project_urls={
        "Paper": "https://arxiv.org/abs/2604.01520",
        "Source": "https://github.com/Paitesanshi/S-Researcher",
    },
)
