from setuptools import setup, find_packages


def _packages():
    # src/ is the yuki_sdk package.
    return ["yuki_sdk"] + [f"yuki_sdk.{name}" for name in find_packages(where="src")]


setup(
    name="yuki-sdk",
    version="0.1.0",
    author="Ward Cornette",
    author_email="Ward.Cornette@curlo.pro",
    description="Unofficial Python SDK for the Nmbrs Accounting (Yuki) SOAP API",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cornettew/yuki-sdk",
    package_dir={"yuki_sdk": "src"},
    packages=_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "zeep>=4.2.0",
        "hvac>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.10",
)
