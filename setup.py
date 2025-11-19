"""
Setup script for InstaAI Studio
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="instaai-studio",
    version="1.0.0",
    author="InstaAI Team",
    description="Create Instagram content with natural language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/instaai-studio",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "moviepy>=1.0.3",
        "ffmpeg-python>=0.2.0",
        "Pillow>=10.2.0",
        "numpy>=1.26.3",
        "anthropic>=0.18.1",
        "openai>=1.12.0",
        "langchain>=0.1.6",
        "instagrapi>=2.1.2",
        "requests>=2.31.0",
        "APScheduler>=3.10.4",
        "python-crontab>=3.0.0",
        "fastapi>=0.109.2",
        "uvicorn>=0.27.1",
        "pydantic>=2.6.1",
        "python-dotenv>=1.0.1",
        "pyyaml>=6.0.1",
        "python-slugify>=8.0.4",
        "tqdm>=4.66.1",
        "colorama>=0.4.6",
        "pydub>=0.25.1",
        "librosa>=0.10.1",
        "sqlalchemy>=2.0.25",
        "click>=8.1.7",
        "python-dateutil>=2.8.2",
    ],
    entry_points={
        "console_scripts": [
            "instaai=main:cli",
        ],
    },
)
